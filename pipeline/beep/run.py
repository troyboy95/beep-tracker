"""Daily pipeline: fetch → normalize → India + eligibility filter → upsert → expire → tag.

Usage (from /pipeline):
  python -m beep.run                     # full run
  python -m beep.run --dry-run           # fetch + filter only; print stats, no DB/LLM
  python -m beep.run --only greenhouse   # limit to one ATS
  python -m beep.run --no-tag            # skip LLM step
"""

import argparse
import logging
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

from beep import db
from beep.config import get_settings
from beep.http import PoliteClient
from beep.normalize import Post, is_india, llm_excerpt, normalize, title_may_be_fresher
from beep.sources import Source, load_sources
from beep.tagger import Tagger

log = logging.getLogger("beep")

MAX_TRANSIENT_RETRIES = 3


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


def tag_pending(conn, settings, run_id: int) -> int:
    tagger = Tagger(settings)
    pending = db.posts_to_tag(conn, settings.max_tag_per_run, llm_excerpt)
    log.info("tagging %d posts in batches of %d", len(pending), settings.gemini_batch_size)
    tagged = 0
    bs = settings.gemini_batch_size
    for i in range(0, len(pending), bs):
        batch = pending[i : i + bs]
        attempt, retry_of, transient = 1, None, 0
        while batch:
            res = tagger.call(batch)
            call_id = db.record_llm_call(conn, run_id, res, attempt, retry_of)  # ledger first
            db.apply_tags(conn, res.tags, call_id, res.model)
            tagged += len(res.tags)
            if res.error and res.retryable and transient < MAX_TRANSIENT_RETRIES:
                transient += 1
                time.sleep(min(60, 5 * 2**transient))
            elif res.error or (res.validation_errors and attempt - transient >= 2):
                # non-retryable, or already retried once for bad output: leave untagged,
                # the next run will pick these up again.
                log.warning("call %s gave up on %d posts: %s", call_id,
                            len(batch) - len(res.tags), res.error or res.validation_errors)
                break
            done = {t.id for t in res.tags}
            batch = [p for p in batch if p.id not in done]
            attempt, retry_of = attempt + 1, call_id
        log.info("tagged %d/%d", tagged, len(pending))
    return tagged


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-tag", action="store_true")
    ap.add_argument("--only", action="append", help="ATS name(s) to include")
    ap.add_argument("--trigger", default="local", choices=["schedule", "manual", "local"])
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    settings = get_settings()
    sources = load_sources(only=set(args.only) if args.only else None)
    log.info("fetching %d boards", len(sources))

    with PoliteClient(settings.http_user_agent, settings.http_timeout_s) as http:
        posts, ok_boards, errors, fetched = fetch_all(sources, http)

    kept = [p for p in posts if p.eligibility.keep]
    reasons = Counter(p.eligibility.reason for p in posts)
    log.info("fetched=%d india(after title pre-check)=%d kept=%d reasons=%s boards_ok=%d/%d",
             fetched, len(posts), len(kept), dict(reasons), len(ok_boards), len(sources))
    if args.dry_run:
        return 0
    if fetched == 0:
        log.error("no posts fetched from any source; aborting")
        return 2

    conn = db.connect(settings.database_url.get_secret_value())
    run_id, started = db.start_run(conn, args.trigger)
    status = "failed"
    stats = {"fetched": fetched, "new": 0, "updated": 0, "expired": 0, "tagged": 0}
    try:
        before = db.existing_hashes(conn)
        stats["new"] = sum((p.source, p.external_id) not in before for p in kept)
        stats["updated"] = sum(
            before.get((p.source, p.external_id), p.content_hash) != p.content_hash for p in kept
        )
        db.upsert_posts(conn, kept)
        stats["expired"] = db.expire_unseen(conn, started, ok_boards)
        if not args.no_tag:
            stats["tagged"] = tag_pending(conn, settings, run_id)
        status = "partial" if errors else "success"
    except Exception as e:
        errors.append({"source": "pipeline", "message": f"{type(e).__name__}: {e}"[:500]})
        log.exception("run failed")
        raise
    finally:
        db.finish_run(conn, run_id, status, stats, errors)
        log.info("run %d %s: %s | public listings: %d", run_id, status, stats,
                 db.public_count(conn))
        conn.close()

    _revalidate(settings)
    return 0


def _revalidate(settings) -> None:
    url = settings.revalidate_url or ""
    if not (url.startswith("https://") and "<" not in url and settings.revalidate_secret):
        log.info("revalidate skipped (REVALIDATE_URL not configured)")
        return
    try:
        httpx.post(
            settings.revalidate_url,
            headers={"Authorization": f"Bearer {settings.revalidate_secret.get_secret_value()}"},
            timeout=15,
        ).raise_for_status()
        log.info("site revalidated")
    except httpx.HTTPError as e:
        log.warning("revalidate failed (site will refresh on its ISR timer): %s", e)


if __name__ == "__main__":
    sys.exit(main())
