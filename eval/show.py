"""Print sampled posts for review: python eval/show.py [start] [end]"""

import json
import sys
from pathlib import Path

posts = json.loads((Path(__file__).parent / "sample.json").read_text(encoding="utf-8"))["posts"]
start, end = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (0, len(posts))
for i, p in enumerate(posts[start:end], start):
    print(f"#{i} id={p['id']} [{p['source']}] {p['company']} | {p['title']}")
    print(f"   loc: {p['location_raw']} | hints: {p['hints'] or '-'} | "
          f"min_yrs_hint={p['min_years_hint']} pre={p['prefilter_reason']}")
    print(f"   MODEL: role={p['role']} | city={p['city']} | type={p['job_type']} | "
          f"fresher={p['is_fresher']} | conf={p['confidence']}")
    print(f"   head: {p['description_head'][:260].replace(chr(10), ' ')}")
    for e in p["evidence"][:7]:
        print(f"     - {e[:200]}")
    print()
