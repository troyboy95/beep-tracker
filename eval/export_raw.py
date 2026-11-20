"""Export raw data behind the findings (read-only) → eval/proofs/raw/

Run from repo root:  PYTHONPATH=pipeline pipeline/.venv/Scripts/python eval/export_raw.py

Files:
  public_jobs.csv      every listing the site shows (with tags and where each city came from)
  ingest_runs.csv      every pipeline run (counts, tokens, cost, queue depth)
  llm_calls.jsonl      the full LLM ledger: one JSON object per call, verbatim request + response
  llm_call_example.json one complete call, pretty-printed (the first successful 15-post call)
"""

import csv
import json
from pathlib import Path

from beep.config import get_settings
from beep.db import connect

OUT = Path(__file__).parent / "proofs" / "raw"


def dump_csv(conn, sql: str, path: Path) -> int:
    cur = conn.execute(sql)
    cols = [d.name for d in cur.description]
    rows = cur.fetchall()
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)
    return len(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    c = connect(get_settings().database_url.get_secret_value())

    n_jobs = dump_csv(c, """
        select p.id, p.source, p.company, p.title, j.location_raw, p.city, j.city_source, p.role,
               p.job_type, j.is_fresher, j.tag_confidence, j.prefilter_reason, j.min_years_hint,
               p.posted_at, p.first_seen_at, j.tag_model, j.tag_prompt_version, j.tag_call_id, p.url
        from public_jobs p join jobs j using (id) order by p.first_seen_at desc, p.id""",
        OUT / "public_jobs.csv")
    n_runs = dump_csv(c, """
        select id, trigger, mode, status, started_at, finished_at, fetched, new_posts,
               updated_posts, expired_posts, tagged, tag_queue_pending, input_tokens,
               output_tokens, est_cost_usd, errors
        from ingest_runs order by id""", OUT / "ingest_runs.csv")

    cur = c.execute("""
        select id, run_id, created_at, model, prompt_version, prompt_hash, job_ids, request,
               response_raw, parsed_ok, validation_errors, input_tokens, output_tokens,
               latency_ms, cost_usd, attempt, retry_of, error
        from llm_calls order by id""")
    cols = [d.name for d in cur.description]
    calls = [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]
    with (OUT / "llm_calls.jsonl").open("w", encoding="utf-8") as f:
        for call in calls:
            f.write(json.dumps(call, ensure_ascii=False, default=str) + "\n")

    example = next(x for x in calls if x["parsed_ok"] and len(x["job_ids"]) == 15
                   and x["prompt_version"] == "v2")
    example = {**example, "response": json.loads(example.pop("response_raw"))}
    (OUT / "llm_call_example.json").write_text(
        json.dumps(example, indent=1, ensure_ascii=False, default=str), encoding="utf-8")

    print(f"public_jobs.csv: {n_jobs} rows | ingest_runs.csv: {n_runs} rows | "
          f"llm_calls.jsonl: {len(calls)} calls | example call #{example['id']}")


if __name__ == "__main__":
    main()
