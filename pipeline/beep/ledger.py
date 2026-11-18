"""Inspect the LLM ledger.

  python -m beep.ledger --run 3        # per-call summary for a run + totals
  python -m beep.ledger --job 1234     # exact input/output behind a job's tag
  python -m beep.ledger --call 57      # full request + raw response of one call
  python -m beep.ledger --cost         # cost per 1,000 tagged posts across all runs
"""

import argparse
import json
import sys

from beep.config import get_settings
from beep.db import connect


def _print_call(conn, call_id: int, job_id: int | None = None) -> None:
    row = conn.execute(
        """select id, run_id, created_at, model, prompt_version, attempt, retry_of, parsed_ok,
                  input_tokens, output_tokens, latency_ms, cost_usd, error, request, response_raw,
                  validation_errors
           from llm_calls where id = %s""",
        (call_id,),
    ).fetchone()
    if not row:
        print(f"call {call_id} not found")
        return
    (cid, run, at, model, pv, attempt, retry_of, ok, inp, outp, lat, cost, err, req, raw,
     verr) = row
    print(f"call {cid} | run {run} | {at:%Y-%m-%d %H:%M:%S} | {model} | prompt {pv} | "
          f"attempt {attempt} (retry_of {retry_of}) | ok={ok}")
    print(f"tokens in/out {inp}/{outp} | {lat} ms | ${cost}")
    if err:
        print(f"error: {err}")
    if verr:
        print(f"validation: {json.dumps(verr)[:500]}")
    posts = req.get("posts", []) if req else []
    items = []
    if raw:
        try:
            items = json.loads(raw).get("items", [])
        except json.JSONDecodeError:
            print(f"raw response (unparseable): {raw[:1000]}")
    if job_id is not None:
        posts = [p for p in posts if p["id"] == job_id]
        items = [i for i in items if i.get("id") == job_id]
    print("\n--- input ---")
    print(json.dumps(posts, indent=2, ensure_ascii=False))
    print("\n--- output ---")
    print(json.dumps(items, indent=2, ensure_ascii=False))


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--run", type=int)
    g.add_argument("--job", type=int)
    g.add_argument("--call", type=int)
    g.add_argument("--cost", action="store_true")
    a = ap.parse_args()
    conn = connect(get_settings().database_url.get_secret_value())

    if a.call:
        _print_call(conn, a.call)
    elif a.job:
        row = conn.execute("select tag_call_id, title from jobs where id = %s",
                           (a.job,)).fetchone()
        if not row or not row[0]:
            print(f"job {a.job} not found or not tagged")
            return 1
        print(f"job {a.job}: {row[1]}")
        _print_call(conn, row[0], job_id=a.job)
    elif a.run:
        rows = conn.execute(
            """select id, attempt, retry_of, parsed_ok, cardinality(job_ids), input_tokens,
                      output_tokens, latency_ms, cost_usd, left(coalesce(error, ''), 60)
               from llm_calls where run_id = %s order by id""",
            (a.run,),
        ).fetchall()
        print("call  att  retry_of  ok     posts  in     out    ms     cost        error")
        for r in rows:
            print("  ".join(str(v if v is not None else "-") for v in r))
        print(f"calls={len(rows)} cost=${sum(r[8] or 0 for r in rows)}")
    else:
        tot = conn.execute(
            """select coalesce(sum(cost_usd), 0), coalesce(sum(input_tokens), 0),
                      coalesce(sum(output_tokens), 0), count(*),
                      count(*) filter (where error is not null)
               from llm_calls"""
        ).fetchone()
        tagged = conn.execute(
            "select count(distinct j) from llm_calls, unnest(job_ids) j where error is null"
        ).fetchone()[0]
        cost, inp, outp, calls, failed = tot
        print(f"calls={calls} (failed={failed}) tokens in/out={inp}/{outp} total=${cost:.6f}")
        print(f"distinct posts sent={tagged}")
        if tagged:
            print(f"cost per 1,000 posts (incl. retries & re-tags): "
                  f"${float(cost) / tagged * 1000:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
