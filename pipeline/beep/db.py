"""Postgres access (plain SQL via psycopg 3). The pipeline is the only writer."""

from collections.abc import Iterable
from datetime import datetime

import psycopg
from psycopg.types.json import Jsonb

from beep.normalize import Post
from beep.tagger import PROMPT_HASH, PROMPT_VERSION, CallResult, PostInput, Tag


def connect(url: str) -> psycopg.Connection:
    return psycopg.connect(url, autocommit=True, connect_timeout=15)


# ------------------------------------------------------------------ runs


def start_run(conn: psycopg.Connection, trigger: str) -> tuple[int, datetime]:
    row = conn.execute(
        "insert into ingest_runs (trigger) values (%s) returning id, started_at", (trigger,)
    ).fetchone()
    return row[0], row[1]


def finish_run(conn: psycopg.Connection, run_id: int, status: str, stats: dict,
               errors: list[dict]) -> None:
    conn.execute(
        """
        update ingest_runs r set
          finished_at = now(), status = %(status)s,
          fetched = %(fetched)s, new_posts = %(new)s, updated_posts = %(updated)s,
          expired_posts = %(expired)s, tagged = %(tagged)s, errors = %(errors)s,
          input_tokens  = coalesce(l.inp, 0),
          output_tokens = coalesce(l.outp, 0),
          est_cost_usd  = coalesce(l.cost, 0)
        from (select sum(input_tokens) inp, sum(output_tokens) outp, sum(cost_usd) cost
              from llm_calls where run_id = %(run_id)s) l
        where r.id = %(run_id)s
        """,
        {**stats, "status": status, "errors": Jsonb(errors), "run_id": run_id},
    )


# ------------------------------------------------------------------ jobs


def existing_hashes(conn: psycopg.Connection) -> dict[tuple[str, str], str]:
    return {
        (s, e): h for s, e, h in conn.execute("select source, external_id, content_hash from jobs")
    }


_UPSERT = """
insert into jobs (source, board, external_id, url, title, company, location_raw, description,
                  hints, posted_at, content_hash, dedup_key, min_years_hint, prefilter_reason)
values (%(source)s, %(board)s, %(external_id)s, %(url)s, %(title)s, %(company)s,
        %(location_raw)s, %(description)s, %(hints)s, %(posted_at)s, %(content_hash)s,
        %(dedup_key)s, %(min_years)s, %(reason)s)
on conflict (source, external_id) do update set
  last_seen_at = now(),
  is_active = true,
  board = excluded.board,
  url = excluded.url,
  posted_at = coalesce(excluded.posted_at, jobs.posted_at),
  -- content_hash covers title/company/location/description/hints, and the remaining fields
  -- derive from them, so overwriting is a no-op unless the content actually changed.
  title = excluded.title, company = excluded.company, location_raw = excluded.location_raw,
  description = excluded.description, hints = excluded.hints, dedup_key = excluded.dedup_key,
  min_years_hint = excluded.min_years_hint, prefilter_reason = excluded.prefilter_reason,
  -- changed content -> clear tags so the post is re-tagged
  tagged_at = case when jobs.content_hash = excluded.content_hash then jobs.tagged_at end,
  content_hash = excluded.content_hash
"""


def upsert_posts(conn: psycopg.Connection, posts: Iterable[Post]) -> None:
    rows = [
        {
            "source": p.source, "board": p.board, "external_id": p.external_id, "url": p.url,
            "title": p.title, "company": p.company, "location_raw": p.location_raw,
            "description": p.description, "hints": p.hints, "posted_at": p.posted_at,
            "content_hash": p.content_hash, "dedup_key": p.dedup_key,
            "min_years": p.eligibility.min_years, "reason": p.eligibility.reason,
        }
        for p in posts
    ]
    with conn.transaction(), conn.cursor() as cur:
        cur.executemany(_UPSERT, rows)


def expire_unseen(conn: psycopg.Connection, run_started: datetime,
                  ok_boards: list[tuple[str, str]]) -> int:
    """Deactivate posts not seen this run — only for boards that fetched successfully."""
    if not ok_boards:
        return 0
    cur = conn.execute(
        """
        update jobs set is_active = false
        where is_active and last_seen_at < %s
          and (source, board) in (select * from unnest(%s::text[], %s::text[]))
        """,
        (run_started, [s for s, _ in ok_boards], [b for _, b in ok_boards]),
    )
    return cur.rowcount


def posts_to_tag(conn: psycopg.Connection, limit: int, excerpt_fn) -> list[PostInput]:
    rows = conn.execute(
        """
        select id, title, company, location_raw, coalesce(hints, ''), min_years_hint, description
        from jobs
        where is_active and (tagged_at is null or tag_prompt_version is distinct from %s)
        order by tagged_at nulls first, first_seen_at, id limit %s
        """,
        (PROMPT_VERSION, limit),
    ).fetchall()
    return [
        PostInput(id=r[0], title=r[1], company=r[2], location=r[3], hints=r[4],
                  min_years_hint=r[5], excerpt=excerpt_fn(r[6] or ""))
        for r in rows
    ]


def apply_tags(conn: psycopg.Connection, tags: list[Tag], call_id: int, model: str) -> None:
    if not tags:
        return
    with conn.transaction(), conn.cursor() as cur:
        cur.executemany(
            """
            update jobs set role = %s, city = %s, job_type = %s, is_fresher = %s,
              tag_confidence = %s, tag_model = %s, tag_prompt_version = %s,
              tag_call_id = %s, tagged_at = now()
            where id = %s
            """,
            [
                (t.role.value, t.city.value, t.job_type.value, t.is_fresher, t.confidence,
                 model, PROMPT_VERSION, call_id, t.id)
                for t in tags
            ],
        )


# ------------------------------------------------------------------ ledger


def record_llm_call(conn: psycopg.Connection, run_id: int | None, res: CallResult,
                    attempt: int, retry_of: int | None) -> int:
    return conn.execute(
        """
        insert into llm_calls (run_id, model, prompt_version, prompt_hash, job_ids, request,
          response_raw, parsed_ok, validation_errors, input_tokens, output_tokens, latency_ms,
          cost_usd, attempt, retry_of, error)
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) returning id
        """,
        (
            run_id, res.model, PROMPT_VERSION, PROMPT_HASH,
            [p["id"] for p in res.request["posts"]], Jsonb(res.request), res.response_raw,
            res.parsed_ok, Jsonb(res.validation_errors) if res.validation_errors else None,
            res.input_tokens, res.output_tokens, res.latency_ms, res.cost_usd, attempt,
            retry_of, res.error,
        ),
    ).fetchone()[0]


def public_count(conn: psycopg.Connection) -> int:
    return conn.execute("select count(*) from public_jobs").fetchone()[0]
