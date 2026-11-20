"""Re-score the SAME 50 posts against the system's current output, after eval fixes 1–3.

Run from repo root:  PYTHONPATH=pipeline pipeline/.venv/Scripts/python eval/rescore_after_fixes.py
Writes eval/labels_after.csv (same gold labels, refreshed model_* columns) and REPORT_after.md.

"System output" = what a user sees once the next full run has applied every fix:
  * role / city / job_type: the post's current tags in the DB (city rule already applied by drains)
  * is_fresher: False if the new deterministic pre-filter drops the post (it would expire and
    never be shown), else the post's current LLM tag. The pre-filter is re-run here on the stored
    title/description because only a *full* run re-filters posts.
"""

import csv
from pathlib import Path

import score
from beep.config import get_settings
from beep.db import connect
from beep.normalize import eligibility

HERE = Path(__file__).parent


def main() -> None:
    before = list(csv.DictReader((HERE / "labels.csv").open(encoding="utf-8")))
    ids = [int(r["id"]) for r in before]
    conn = connect(get_settings().database_url.get_secret_value())
    cur = {
        r[0]: r[1:]
        for r in conn.execute(
            """select id, title, coalesce(hints,''), coalesce(description,''), role, city,
                      city_source, job_type, is_fresher, is_active, tag_status
               from jobs where id = any(%s)""",
            (ids,),
        )
    }

    after, changes = [], []
    for r in before:
        title, hints, desc, role, city, city_src, jtype, fresher, active, status = cur[int(r["id"])]
        dropped = not eligibility(title, f"{hints}\n{desc}").keep
        new = {
            "model_role": role,
            "model_city": city,
            "model_job_type": jtype,
            "model_is_fresher": str(False if dropped else fresher),
        }
        for k, v in new.items():
            if r[k] != v:
                why = "pre-filter now drops it" if k == "model_is_fresher" and dropped else (
                    f"city_source={city_src}" if k == "model_city" else "re-tagged")
                changes.append((r["id"], r["title"][:55], k[6:], r[k], v, why))
        if not active or status != "done":
            changes.append((r["id"], r["title"][:55], "state", "", f"active={active} {status}", ""))
        after.append({**r, **new})

    with (HERE / "labels_after.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(before[0].keys()))
        w.writeheader()
        w.writerows(after)

    print(f"{len(changes)} tag changes on the 50 sampled posts:")
    for c in changes:
        print("  ", " | ".join(map(str, c)))
    print()
    score.main("labels_after.csv", "REPORT_after.md", " (after fixes 1–3)")


if __name__ == "__main__":
    main()
