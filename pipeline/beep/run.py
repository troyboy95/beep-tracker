"""Pipeline entrypoint.

  python -m beep.run                     # full: fetch → filter → upsert → expire → drain tag queue
  python -m beep.run --tag-only          # drain the tagging queue only (cheap, run often)
  python -m beep.run --dry-run           # fetch + filter only; print stats, no DB/LLM
  python -m beep.run --only greenhouse   # limit fetching to one ATS (repeatable)
  python -m beep.run --no-tag            # full run without the LLM step
"""

import argparse
import logging
import os
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

from beep import db, tag_queue
from beep.config import get_settings
from beep.http import PoliteClient
from beep.normalize import Post, is_india, normalize, title_may_be_fresher
from beep.sources import Source, load_sources

log = logging.getLogger("beep")


def fetch_all(sources: list[Source], http: PoliteClient):
    """Fetch every board concurrently. A failing board is recorded, never fatal."""
    posts: list[Post] = []
    ok_boards: list[tuple[str, str]] = []
    errors: list[dict] = []
    fetched = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(s.fetch, http, title_may_be_fresher): s for s in sources}
        for fut in as_completed(futs):
            s = futs[fut]
            try:
                raws = fut.result()
            except Exception as e:  # noqa: BLE001
                msg = f"{type(e).__name__}: {str(e)[:200]}"
                log.warning("source %s/%s failed: %s", s.name, s.board, msg)
                errors.append({"source": s.name, "board": s.board, "message": msg})
                continue
            ok_boards.append((s.name, s.board))
            fetched += len(raws)
            posts.extend(normalize(r) for r in raws if is_india(r.location_raw))
    return posts, ok_boards, errors, fetched


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-tag", action="store_true")
    ap.add_argument("--tag-only", action="store_true")
    ap.add_argument("--only", action="append", help="ATS name(s) to include")
    ap.add_argument("--trigger", default="local", choices=["schedule", "manual", "local"])
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    settings = get_settings()

    kept, ok_boards, errors, fetched = [], [], [], 0
    if not args.tag_only:
        sources = load_sources(only=set(args.only) if args.only else None)
        log.info("fetching %d boards", len(sources))
        with PoliteClient(settings.http_user_agent, settings.http_timeout_s) as http:
            posts, ok_boards, errors, fetched = fetch_all(sources, http)
        kept = [p for p in posts if p.eligibility.keep]
        log.info("fetched=%d india=%d kept=%d reasons=%s boards_ok=%d/%d", fetched, len(posts),
                 len(kept), dict(Counter(p.eligibility.reason for p in posts)), len(ok_boards),
                 len(sources))
        if args.dry_run:
            return 0
        if fetched == 0:
            log.error("no posts fetched from any source; aborting")
            return 2

    conn = db.connect(settings.database_url.get_secret_value())
    mode = "tag_only" if args.tag_only else "full"
    run_id, started = db.start_run(conn, args.trigger, mode)
    status = "failed"
    stats = {"fetched": fetched, "new": 0, "updated": 0, "expired": 0, "tagged": 0, "queue": None}
    try:
        if not args.tag_only:
            before = db.existing_hashes(conn)
            stats["new"] = sum((p.source, p.external_id) not in before for p in kept)
            stats["updated"] = sum(
                before.get((p.source, p.external_id), p.content_hash) != p.content_hash
                for p in kept
            )
            db.upsert_posts(conn, kept)
            stats["expired"] = db.expire_unseen(conn, started, ok_boards)
        if not args.no_tag:
            stats["tagged"] = tag_queue.drain(conn, settings, run_id)
        stats["queue"] = db.queue_depth(conn)
        status = "partial" if errors else "success"
    except Exception as e:
        errors.append({"source": "pipeline", "message": f"{type(e).__name__}: {e}"[:500]})
        log.exception("run failed")
        raise
    finally:
        db.finish_run(conn, run_id, status, stats, errors)
        public = db.public_count(conn)
        log.info("run %d (%s) %s: %s | public listings: %d", run_id, mode, status, stats, public)
        _step_summary(run_id, mode, status, stats, public, errors)
        conn.close()

    if stats["tagged"] or stats["new"] or stats["expired"]:
        _revalidate(settings)
    return 0


def _step_summary(run_id, mode, status, stats, public, errors) -> None:
    """Markdown summary on the GitHub Actions run page (no-op locally)."""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    lines = [
        f"## Beep pipeline — run {run_id} ({mode}): **{status}**",
        "",
        "| fetched | new | updated | expired | tagged | queue pending | public listings |",
        "|---|---|---|---|---|---|---|",
        f"| {stats['fetched']} | {stats['new']} | {stats['updated']} | {stats['expired']} "
        f"| {stats['tagged']} | {stats['queue']} | {public} |",
    ]
    if errors:
        lines += ["", "### Errors", *[f"- `{e.get('source')}/{e.get('board', '')}`: "
                                      f"{e.get('message', '')[:200]}" for e in errors]]
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _revalidate(settings) -> None:
    url = settings.revalidate_url or ""
    if not (url.startswith("https://") and "<" not in url and settings.revalidate_secret):
        log.info("revalidate skipped (REVALIDATE_URL not configured)")
        return
    try:
        httpx.post(
            url,
            headers={"Authorization": f"Bearer {settings.revalidate_secret.get_secret_value()}"},
            timeout=15,
        ).raise_for_status()
        log.info("site revalidated")
    except httpx.HTTPError as e:
        log.warning("revalidate failed (site will refresh on its ISR timer): %s", e)


if __name__ == "__main__":
    sys.exit(main())
