-- Durable tagging queue on `jobs`: survives runs/deploys, backs off on failures,
-- parks poison rows instead of retrying them forever.
--
--   pending ──tag ok──▶ done
--      │  ▲                │ content or prompt version changes
--      │  └────────────────┘
--      └─ bad output × N ──▶ failed   (manual review; re-queue with tag_status='pending')
-- Transient errors (429/5xx) only push `next_tag_at` forward; they never count toward `failed`.

alter table public.jobs add column if not exists tag_status text not null default 'pending'
  check (tag_status in ('pending', 'done', 'failed'));
alter table public.jobs add column if not exists tag_attempts  smallint not null default 0;
alter table public.jobs add column if not exists next_tag_at   timestamptz;
alter table public.jobs add column if not exists last_tag_error text;

update public.jobs set tag_status = 'done' where tagged_at is not null and tag_status = 'pending';

create index if not exists jobs_tag_queue_idx
  on public.jobs (next_tag_at nulls first, first_seen_at)
  where is_active and tag_status = 'pending';

drop index if exists public.jobs_untagged_idx;

-- Queue depth for monitoring, and run mode: 'full' (fetch + tag) or 'tag_only' (queue drain).
alter table public.ingest_runs add column if not exists tag_queue_pending integer;
alter table public.ingest_runs add column if not exists mode text not null default 'full'
  check (mode in ('full', 'tag_only'));
grant select (tag_queue_pending, mode) on public.ingest_runs to anon, authenticated;
