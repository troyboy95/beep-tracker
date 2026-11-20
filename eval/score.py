"""Score hand-checked labels and write eval/REPORT.md.

Run from repo root:  PYTHONPATH=pipeline pipeline/.venv/Scripts/python eval/score.py
Edit eval/labels.csv (gold_* columns, alt_ok, notes), then re-run; the report is regenerated.

strict  = model value equals the gold label
lenient = also accepts the model's value when the reviewer marked it a defensible
          alternative (`alt_ok` lists those fields for that post)
"""

import csv
import json
import math
from pathlib import Path

HERE = Path(__file__).parent
FIELDS = ["role", "city", "job_type", "is_fresher"]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def pct(k: int, n: int) -> str:
    lo, hi = wilson(k, n)
    return f"{k}/{n} = **{k / n:.0%}** (95% CI {lo:.0%}–{hi:.0%})"


def ledger_cost() -> dict | None:
    try:
        from beep.config import get_settings
        from beep.db import connect
    except ImportError:
        return None
    s = get_settings()
    c = connect(s.database_url.get_secret_value())
    tot_cost, calls, failed = c.execute(
        "select coalesce(sum(cost_usd),0), count(*), count(*) filter (where error is not null)"
        " from llm_calls").fetchone()
    tagged = c.execute(
        "select count(distinct j) from llm_calls, unnest(job_ids) j where parsed_ok").fetchone()[0]
    ok_cost, ok_posts, inp, outp = c.execute(
        "select coalesce(sum(cost_usd),0), coalesce(sum(cardinality(job_ids)),0),"
        " coalesce(sum(input_tokens),0), coalesce(sum(output_tokens),0)"
        " from llm_calls where parsed_ok").fetchone()
    return {
        "model": s.gemini_model, "price_in": s.gemini_price_input_per_m,
        "price_out": s.gemini_price_output_per_m, "calls": calls, "failed": failed,
        "total_cost": float(tot_cost), "posts_tagged": tagged,
        "all_in_per_1k": float(tot_cost) / tagged * 1000 if tagged else None,
        "per_1k_successful": float(ok_cost) / ok_posts * 1000 if ok_posts else None,
        "tok_in_per_post": inp / ok_posts if ok_posts else None,
        "tok_out_per_post": outp / ok_posts if ok_posts else None,
    }


def main(labels: str = "labels.csv", out: str = "REPORT.md", title: str = "") -> None:
    rows = list(csv.DictReader((HERE / labels).open(encoding="utf-8")))
    meta = json.loads((HERE / "sample.json").read_text(encoding="utf-8"))["meta"]
    n = len(rows)
    if any(not r[f"gold_{f}"] for r in rows for f in FIELDS):
        raise SystemExit("labels.csv has empty gold_* cells; finish labelling first")

    def correct(r, f, lenient):
        if r[f"model_{f}"] == r[f"gold_{f}"]:
            return True
        return lenient and f in r["alt_ok"].split(";")

    lines = [f"# Tagging accuracy: 50-post hand check{title}", ""]
    lines += [
        f"- Sample: {n} posts drawn at random (seed `{meta['seed']}`) from "
        f"**{meta['population_active_tagged']} active tagged posts** on {meta['drawn_at'][:10]}. "
        "This includes posts the model *rejected* as non-fresher, so `is_fresher` is tested both ways.",
        f"- Reviewer: {rows[0]['reviewer']}. Gold labels follow the same written rules as the "
        "prompt (fresher = minimum required experience ≤ 2 yrs, or none stated and not a "
        "senior/managerial role).",
        "- *Strict* = exact match. *Lenient* also accepts a different-but-defensible label the "
        "reviewer marked `alt_ok`.",
        "",
        "## Accuracy per field",
        "",
        "| Field | Strict | Lenient |",
        "|---|---|---|",
    ]
    for f in FIELDS:
        ks = sum(correct(r, f, False) for r in rows)
        kl = sum(correct(r, f, True) for r in rows)
        lines.append(f"| {f} | {pct(ks, n)} | {pct(kl, n)} |")
    ks = sum(all(correct(r, f, False) for f in FIELDS) for r in rows)
    kl = sum(all(correct(r, f, True) for f in FIELDS) for r in rows)
    lines.append(f"| **all 4 fields** | {pct(ks, n)} | {pct(kl, n)} |")

    tp = sum(r["model_is_fresher"] == "True" and r["gold_is_fresher"] == "True" for r in rows)
    fp = sum(r["model_is_fresher"] == "True" and r["gold_is_fresher"] == "False" for r in rows)
    fn = sum(r["model_is_fresher"] == "False" and r["gold_is_fresher"] == "True" for r in rows)
    lines += [
        "",
        "## What users see: the fresher filter",
        "",
        f"- **Precision** (shown posts that really are fresher-eligible): {pct(tp, tp + fp)}",
        f"- **Recall** (fresher-eligible posts that get shown): {pct(tp, tp + fn)}",
        "",
        "## Every disagreement",
        "",
        "| id | Post | Field | Model | Gold | Defensible? | Note |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        for f in FIELDS:
            if r[f"model_{f}"] != r[f"gold_{f}"]:
                alt = "yes" if f in r["alt_ok"].split(";") else "no"
                title = f"{r['company']}: {r['title']}"[:60].replace("|", "/")
                lines.append(f"| {r['id']} | {title} | {f} | {r[f'model_{f}']} | "
                             f"{r[f'gold_{f}']} | {alt} | {r['notes']} |")

    cost = ledger_cost()
    if cost:
        lines += [
            "",
            "## Cost per 1,000 posts",
            "",
            f"Model `{cost['model']}` at **paid-tier** prices of ${cost['price_in']}/M input and "
            f"${cost['price_out']}/M output tokens (the free tier was actually used, so the bill was $0).",
            "",
            "| Measure | Value |",
            "|---|---|",
            f"| LLM calls (incl. failed 503/429, billed $0) | {cost['calls']} ({cost['failed']} failed) |",
            f"| Tokens per post (successful calls) | {cost['tok_in_per_post']:.0f} in / "
            f"{cost['tok_out_per_post']:.0f} out |",
            f"| Cost per 1,000 posts, tagging only | **${cost['per_1k_successful']:.3f}** |",
            f"| Cost per 1,000 posts, all-in (retries + re-tags after prompt changes) | "
            f"**${cost['all_in_per_1k']:.3f}** |",
            "| Infrastructure (Vercel Hobby, Supabase Free, GitHub Actions public, Gemini free tier) | $0 |",
        ]
    (HERE / out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    import sys

    main(*sys.argv[1:4])
