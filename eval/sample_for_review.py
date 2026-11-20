"""Draw a reproducible random sample of tagged posts for hand-checking.

Run from repo root:  PYTHONPATH=pipeline pipeline/.venv/Scripts/python eval/sample_for_review.py
Writes eval/sample.json (full context per post) and eval/labels.csv (model tags + empty gold cols).

The sample is drawn from ALL active tagged posts (not only public/fresher ones) so that
`is_fresher` is evaluated on both accepted and rejected posts.
"""

import csv
import json
import random
import re
from datetime import UTC, datetime
from pathlib import Path

from beep.config import get_settings
from beep.db import connect

N = 50
SEED = 20261120
HERE = Path(__file__).parent
EXP = re.compile(
    r"[^.\n]*(experience|years|yrs|fresher|graduat|intern|entry|junior|senior|location|based in"
    r"|office|hybrid|remote|degree|b\.?tech|mba)[^.\n]*",
    re.I,
)


def main() -> None:
    conn = connect(get_settings().database_url.get_secret_value())
    rows = conn.execute(
        """
        select id, source, company, title, location_raw, coalesce(hints, ''), min_years_hint,
               prefilter_reason, role, city, job_type, is_fresher, tag_confidence, tag_model,
               tag_prompt_version, tag_call_id, url, coalesce(description, '')
        from jobs
        where is_active and tag_status = 'done'
        order by id
        """
    ).fetchall()
    population = len(rows)
    sample = sorted(random.Random(SEED).sample(rows, N), key=lambda r: r[0])

    cols = ["id", "source", "company", "title", "location_raw", "hints", "min_years_hint",
            "prefilter_reason", "role", "city", "job_type", "is_fresher", "confidence",
            "model", "prompt_version", "call_id", "url"]
    out = []
    for r in sample:
        d = dict(zip(cols, r[:17], strict=True))
        desc = r[17]
        d["description_head"] = desc[:700]
        d["evidence"] = [m.group(0).strip()[:260] for m in EXP.finditer(desc)][:12]
        out.append(d)

    meta = {"drawn_at": datetime.now(UTC).isoformat(timespec="seconds"), "seed": SEED,
            "population_active_tagged": population, "n": N}
    (HERE / "sample.json").write_text(
        json.dumps({"meta": meta, "posts": out}, indent=1, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    with (HERE / "labels.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "company", "title", "location_raw", "model_role", "model_city",
                    "model_job_type", "model_is_fresher", "gold_role", "gold_city",
                    "gold_job_type", "gold_is_fresher", "reviewer", "notes"])
        for d in out:
            w.writerow([d["id"], d["company"], d["title"], d["location_raw"], d["role"], d["city"],
                        d["job_type"], d["is_fresher"], "", "", "", "", "", ""])
    print(f"sampled {N} of {population} active tagged posts (seed {SEED})")


if __name__ == "__main__":
    main()
