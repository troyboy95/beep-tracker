"""Collect the evidence behind the three findings (read-only) → eval/proofs/evidence.json.

Run from repo root:  PYTHONPATH=pipeline pipeline/.venv/Scripts/python eval/proofs.py
Every number in the "findings and proof" doc comes from this script's output.
"""

import csv
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from beep.cities import resolve_city
from beep.config import REPO_ROOT, get_settings
from beep.db import connect
from beep.normalize import is_senior_title

HERE = Path(__file__).parent
OUT = HERE / "proofs"


def llm_city_for(response_raw: str | None, job_id: int) -> str | None:
    try:
        for item in json.loads(response_raw or "")["items"]:
            if item.get("id") == job_id:
                return item.get("city")
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return None


def main() -> None:
    s = get_settings()
    c = connect(s.database_url.get_secret_value())
    ev: dict = {"collected_at": datetime.now(UTC).isoformat(timespec="seconds")}

    # ---------------------------------------------------------------- Finding 1: cities
    rows = c.execute(
        """select j.id, j.source, j.title, j.location_raw, j.city, l.id, l.response_raw
           from jobs j join llm_calls l on l.id = j.tag_call_id
           where j.city_source = 'rule'"""
    ).fetchall()
    corrected = []
    for jid, src, title, loc, city, call_id, raw in rows:
        llm = llm_city_for(raw, jid)
        if llm and llm != city:
            corrected.append({"id": jid, "source": src, "title": title, "location_raw": loc,
                              "llm_city": llm, "final_city": city, "ledger_call": call_id})
    other_now = c.execute(
        "select location_raw from jobs where is_active and city = 'Other (India)'").fetchall()
    ev["f1"] = {
        "rule_rows": len(rows),
        "corrected_vs_llm": len(corrected),
        "transitions": Counter(f"{r['llm_city']} -> {r['final_city']}" for r in corrected).most_common(),
        "by_source": Counter(r["source"] for r in corrected).most_common(),
        "examples": corrected[:8],
        "other_india_now": len(other_now),
        "other_india_now_naming_listed_city": sum(resolve_city(loc) is not None for (loc,) in other_now),
        "city_source_split": c.execute(
            "select city_source, count(*) from jobs where tag_status='done' group by 1 order by 1"
        ).fetchall(),
    }

    # ---------------------------------------------------------------- Finding 2: LLM failures
    calls = c.execute(
        """select id, run_id, attempt, retry_of, parsed_ok, coalesce(error,''), cardinality(job_ids),
                  latency_ms, created_at from llm_calls order by id""").fetchall()

    def err_class(e: str) -> str:
        m = re.match(r"APIError (\d+)", e)
        return m.group(1) if m else ("other" if e else "ok")

    per_run: dict = {}
    for _, run, *_rest in calls:
        per_run.setdefault(run, Counter())
    for cid, run, att, rof, ok, err, n, lat, at in calls:
        per_run[run][err_class(err)] += 1
    first_503 = next((x for x in calls if x[5].startswith("APIError 503")), None)
    retried_ok = sum(1 for x in calls if x[4] and x[3] is not None)
    ev["f2"] = {
        "calls": len(calls),
        "failed": sum(1 for x in calls if x[5]),
        "by_class": Counter(err_class(x[5]) for x in calls).most_common(),
        "per_run": {str(k): dict(v) for k, v in per_run.items()},
        "succeeded_on_retry": retried_ok,
        "sample_error": {"call": first_503[0], "run": first_503[1], "attempt": first_503[2],
                         "error": first_503[5][:220], "at": first_503[8].isoformat()} if first_503 else None,
        "runs": [dict(zip(["id", "trigger", "mode", "status", "started", "fetched", "new", "expired",
                           "tagged", "queue_after"], (r[0], r[1], r[2], r[3], r[4].isoformat(), *r[5:]),
                          strict=True))
                 for r in c.execute(
                     "select id, trigger, mode, status, started_at, fetched, new_posts, expired_posts,"
                     " tagged, tag_queue_pending from ingest_runs order by id").fetchall()],
        "queue_now": c.execute(
            "select tag_status, count(*) from jobs where is_active group by 1 order by 1").fetchall(),
    }

    # ---------------------------------------------------------------- Finding 3: fresher by title
    probe = json.loads((REPO_ROOT / "pipeline/scripts/probe_results.json").read_text(encoding="utf-8"))
    labels_b = list(csv.DictReader((HERE / "labels.csv").open(encoding="utf-8")))
    labels_a = list(csv.DictReader((HERE / "labels_after.csv").open(encoding="utf-8")))

    def fp(rows):
        return [{"id": r["id"], "company": r["company"], "title": r["title"]} for r in rows
                if r["model_is_fresher"] == "True" and r["gold_is_fresher"] == "False"]

    active = c.execute("select id, title from jobs where is_active and tag_status='done'").fetchall()
    public_ids = {i for (i,) in c.execute("select id from public_jobs").fetchall()}
    senior = [(i, t) for i, t in active if is_senior_title(t)]
    ev["f3"] = {
        "probe_boards_with_india": len(probe),
        "probe_india_posts": sum(p["india"] for p in probe),
        "probe_title_fresher": sum(p["fresher"] for p in probe),
        "prefilter_reason_active": c.execute(
            "select prefilter_reason, count(*) from jobs where is_active group by 1 order by 2 desc"
        ).fetchall(),
        "fresher_split_active": c.execute(
            "select is_fresher, count(*) from jobs where is_active and tag_status='done' group by 1"
        ).fetchall(),
        "public_now": len(public_ids),
        "eval_false_positives_before": fp(labels_b),
        "eval_false_positives_after": fp(labels_a),
        "senior_title_active": len(senior),
        "senior_title_public": sum(i in public_ids for i, _ in senior),
        "senior_title_examples": [t for _, t in senior][:10],
    }

    # ---------------------------------------------------------------- cost
    tot, tin, tout = c.execute(
        "select coalesce(sum(cost_usd),0), coalesce(sum(input_tokens),0), coalesce(sum(output_tokens),0)"
        " from llm_calls").fetchone()
    okc, okn, oki, oko = c.execute(
        "select sum(cost_usd), sum(cardinality(job_ids)), sum(input_tokens), sum(output_tokens)"
        " from llm_calls where parsed_ok").fetchone()
    distinct = c.execute(
        "select count(distinct j) from llm_calls, unnest(job_ids) j where parsed_ok").fetchone()[0]
    ev["cost"] = {
        "model": s.gemini_model, "price_in_per_m": s.gemini_price_input_per_m,
        "price_out_per_m": s.gemini_price_output_per_m,
        "total_usd": round(float(tot), 6), "tokens_in": tin, "tokens_out": tout,
        "distinct_posts_tagged": distinct,
        "per_1k_tagging_only": round(float(okc) / okn * 1000, 4),
        "per_1k_all_in": round(float(tot) / distinct * 1000, 4),
        "tokens_per_post": [round(oki / okn), round(oko / okn)],
        "db_size": c.execute("select pg_size_pretty(pg_database_size(current_database()))").fetchone()[0],
    }

    OUT.mkdir(exist_ok=True)
    (OUT / "evidence.json").write_text(json.dumps(ev, indent=1, default=str), encoding="utf-8")
    print(json.dumps(ev, indent=1, default=str))


if __name__ == "__main__":
    main()
