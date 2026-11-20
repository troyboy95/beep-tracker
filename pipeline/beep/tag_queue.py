"""Tagging queue worker.

The queue is durable state on `jobs` (tag_status / next_tag_at / tag_attempts), so pending work
survives across runs and deploys. A run drains what is due, within free-tier limits:

* every API call is written to the ledger before its tags are applied
* 429/5xx → in-run retries honoring the server's `retryDelay`, then back to the queue with a
  backoff (never counted as a failure)
* daily quota exhausted → stop immediately; everything left stays pending for the next run
* N consecutive batches failing transiently → circuit breaker, stop calling the provider
* malformed output → one immediate retry, then backoff; after MAX_BAD_OUTPUT attempts the post
  is parked as 'failed' for manual review
"""

import logging
import time
from dataclasses import dataclass

from beep import db
from beep.cities import resolve_city
from beep.normalize import llm_excerpt
from beep.tagger import PostInput, Tag, Tagger

log = logging.getLogger("beep.tag_queue")

MAX_TRANSIENT_RETRIES = 3  # per batch, within a run
MAX_RETRY_SLEEP_S = 60
TRANSIENT_BACKOFF_S = 30 * 60  # queue-level: retry on a later drain run
BAD_OUTPUT_BACKOFF_S = 2 * 60 * 60
MAX_BAD_OUTPUT = 3
CIRCUIT_BREAK_AFTER = 4  # consecutive transiently-failed batches


@dataclass
class BatchOutcome:
    tagged: int
    leftover: list[PostInput]
    kind: str  # ok | transient | quota | bad
    error: str = ""


def _apply_city_rule(tags: list[Tag], batch: list[PostInput]) -> dict[int, str]:
    """Override the LLM's city where the location names exactly one listed city.
    Mutates `tags` (after the ledger has stored the raw response); returns id -> source."""
    loc = {p.id: p.location for p in batch}
    source: dict[int, str] = {}
    for t in tags:
        rule = resolve_city(loc.get(t.id))
        if rule is not None:
            t.city = rule
            source[t.id] = "rule"
        else:
            source[t.id] = "llm"
    return source


def _tag_batch(conn, tagger: Tagger, run_id: int, batch: list[PostInput]) -> BatchOutcome:
    tagged, attempt, transient, bad = 0, 1, 0, 0
    call_id = None
    while True:
        res = tagger.call(batch)
        call_id = db.record_llm_call(conn, run_id, res, attempt, call_id)  # ledger first
        sources = _apply_city_rule(res.tags, batch)
        db.apply_tags(conn, res.tags, call_id, res.model, sources)
        tagged += len(res.tags)
        done = {t.id for t in res.tags}
        batch = [p for p in batch if p.id not in done]
        if not batch:
            return BatchOutcome(tagged, [], "ok")

        if res.quota_exhausted:
            return BatchOutcome(tagged, batch, "quota", res.error or "")
        if res.error and res.retryable:
            if transient >= MAX_TRANSIENT_RETRIES:
                return BatchOutcome(tagged, batch, "transient", res.error)
            transient += 1
            wait = res.retry_after_s or 5 * 2**transient
            time.sleep(min(MAX_RETRY_SLEEP_S, wait + 1))
        elif res.error:  # non-retryable API error (e.g. 400)
            return BatchOutcome(tagged, batch, "bad", res.error)
        else:  # parsed, but missing/invalid items
            if bad >= 1:
                return BatchOutcome(tagged, batch, "bad", str(res.validation_errors)[:500])
            bad += 1
        attempt += 1


def drain(conn, settings, run_id: int) -> int:
    """Tag due items from the queue. Returns number of posts tagged this run."""
    requeued = db.requeue_stale_prompt(conn)
    if requeued:
        log.info("re-queued %d posts tagged with an older prompt version", requeued)
    fixed, requeued_city = db.apply_city_rules(conn, resolve_city)
    if fixed or requeued_city:
        log.info("city rule: corrected %d posts, re-queued %d for the LLM", fixed, requeued_city)

    due = db.posts_to_tag(conn, settings.max_tag_per_run, llm_excerpt)
    log.info("queue: %d due now (depth %d), batches of %d",
             len(due), db.queue_depth(conn), settings.gemini_batch_size)
    if not due:
        return 0

    tagger = Tagger(settings)
    bs = settings.gemini_batch_size
    tagged, consecutive_transient = 0, 0
    for i in range(0, len(due), bs):
        out = _tag_batch(conn, tagger, run_id, due[i : i + bs])
        tagged += out.tagged
        ids = [p.id for p in out.leftover]
        if out.kind == "bad":
            db.defer_posts(conn, ids, out.error, BAD_OUTPUT_BACKOFF_S, True, MAX_BAD_OUTPUT)
        elif out.kind in ("transient", "quota"):
            db.defer_posts(conn, ids, out.error, TRANSIENT_BACKOFF_S, False, MAX_BAD_OUTPUT)

        if out.kind == "quota":
            log.warning("daily LLM quota exhausted; stopping. %d posts remain queued",
                        len(due) - i - bs + len(ids))
            break
        consecutive_transient = consecutive_transient + 1 if out.kind == "transient" else 0
        if consecutive_transient >= CIRCUIT_BREAK_AFTER:
            log.warning("provider unhealthy (%d batches in a row failed); stopping, "
                        "remaining posts stay queued", consecutive_transient)
            break
        log.info("tagged %d/%d", tagged, len(due))
    return tagged
