-- Beep Tracker — database schema (Postgres / Supabase)
-- Apply once in Supabase SQL Editor. Safe to re-run: objects use IF NOT EXISTS / OR REPLACE.
--
-- Access model:
--   * Pipeline connects as `postgres` via the Supavisor pooler (DATABASE_URL) and bypasses RLS.
--   * Web app uses the publishable (anon) key: read-only on active jobs + refresh status.
--   * `llm_calls` (ledger) is never exposed to anon/authenticated.

-- ---------------------------------------------------------------------------
-- 1. Ingest runs: one row per pipeline execution
-- ---------------------------------------------------------------------------
create table if not exists public.ingest_runs (
  id              bigint generated always as identity primary key,
  started_at      timestamptz not null default now(),
  finished_at     timestamptz,
  status          text not null default 'running'
                  check (status in ('running', 'success', 'partial', 'failed')),
  trigger         text not null default 'schedule'
                  check (trigger in ('schedule', 'manual', 'local')),
  fetched         integer not null default 0,   -- raw posts returned by all sources
  new_posts       integer not null default 0,   -- inserted this run
  updated_posts   integer not null default 0,   -- content changed this run
  expired_posts   integer not null default 0,   -- marked inactive this run
  tagged          integer not null default 0,   -- posts tagged by LLM this run
  input_tokens    bigint  not null default 0,   -- roll-up of llm_calls
  output_tokens   bigint  not null default 0,
  est_cost_usd    numeric(12, 6) not null default 0,
  errors          jsonb   not null default '[]'::jsonb  -- [{source, message}]
);

create index if not exists ingest_runs_finished_idx
  on public.ingest_runs (finished_at desc) where status in ('success', 'partial');

-- ---------------------------------------------------------------------------
-- 2. LLM ledger: append-only, one row per API call (incl. failures & retries)
-- ---------------------------------------------------------------------------
create table if not exists public.llm_calls (
  id                 bigint generated always as identity primary key,
  run_id             bigint references public.ingest_runs (id) on delete set null,
  created_at         timestamptz not null default now(),
  provider           text not null default 'gemini',
  model              text not null,
  prompt_version     text not null,
  prompt_hash        text not null,              -- sha256 of system prompt + schema
  job_ids            bigint[] not null default '{}',
  request            jsonb,                      -- exact inputs sent (posts payload)
  response_raw       text,                       -- verbatim model output
  parsed_ok          boolean not null default false,
  validation_errors  jsonb,
  input_tokens       integer,
  output_tokens      integer,
  latency_ms         integer,
  cost_usd           numeric(14, 8),             -- at configured paid-tier prices
  attempt            smallint not null default 1,
  retry_of           bigint references public.llm_calls (id),
  error              text
);

create index if not exists llm_calls_run_idx  on public.llm_calls (run_id);
create index if not exists llm_calls_jobs_idx on public.llm_calls using gin (job_ids);

-- Append-only guard. Retention jobs may null out payloads only when they
-- explicitly opt in with: SET LOCAL app.ledger_maintenance = 'on';
create or replace function public.llm_calls_append_only()
returns trigger language plpgsql as $$
begin
  if coalesce(current_setting('app.ledger_maintenance', true), 'off') <> 'on' then
    raise exception 'llm_calls is append-only (set app.ledger_maintenance=on for retention jobs)';
  end if;
  return case when tg_op = 'DELETE' then old else new end;
end $$;

drop trigger if exists llm_calls_append_only on public.llm_calls;
create trigger llm_calls_append_only
  before update or delete on public.llm_calls
  for each row execute function public.llm_calls_append_only();

-- ---------------------------------------------------------------------------
-- 3. Jobs
-- ---------------------------------------------------------------------------
create table if not exists public.jobs (
  id                  bigint generated always as identity primary key,
  source              text not null,             -- greenhouse | lever | ashby | smartrecruiters | adzuna
  external_id         text not null,             -- id within the source
  url                 text not null,
  title               text not null,
  company             text not null,
  location_raw        text,
  description         text,                      -- cleaned, trimmed plain text
  posted_at           timestamptz,
  first_seen_at       timestamptz not null default now(),
  last_seen_at        timestamptz not null default now(),
  is_active           boolean not null default true,
  content_hash        text not null,             -- re-tag only when this changes
  dedup_key           text not null,             -- hash(norm company + title + city) for cross-source dedup
  -- LLM tags (null until tagged)
  role                text,
  city                text,
  job_type            text check (job_type in ('internship', 'full_time', 'other')),
  is_fresher          boolean,
  tag_confidence      real check (tag_confidence between 0 and 1),
  tag_model           text,
  tag_prompt_version  text,
  tagged_at           timestamptz,
  tag_call_id         bigint references public.llm_calls (id),
  search_tsv          tsvector generated always as (
                        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
                        setweight(to_tsvector('english', coalesce(company, '')), 'B') ||
                        setweight(to_tsvector('english', coalesce(role, '') || ' ' || coalesce(city, '')), 'B') ||
                        setweight(to_tsvector('english', left(coalesce(description, ''), 2000)), 'C')
                      ) stored,
  unique (source, external_id)
);

create index if not exists jobs_dedup_idx       on public.jobs (dedup_key);
create index if not exists jobs_active_idx      on public.jobs (is_active, first_seen_at desc);
create index if not exists jobs_role_city_idx   on public.jobs (role, city) where is_active;
create index if not exists jobs_search_idx      on public.jobs using gin (search_tsv);
create index if not exists jobs_untagged_idx    on public.jobs (id) where tagged_at is null;

-- Public listing: active, tagged, fresher posts; one row per dedup_key (earliest seen wins).
create or replace view public.public_jobs
with (security_invoker = true) as
select distinct on (dedup_key)
  id, source, url, title, company, location_raw, posted_at, first_seen_at,
  role, city, job_type, search_tsv
from public.jobs
where is_active
  and is_fresher is true
  and tagged_at is not null
order by dedup_key, first_seen_at, id;

-- ---------------------------------------------------------------------------
-- 4. Row Level Security & grants
-- ---------------------------------------------------------------------------
alter table public.jobs        enable row level security;
alter table public.ingest_runs enable row level security;
alter table public.llm_calls   enable row level security;

-- Supabase grants table privileges to anon/authenticated by default; tighten them.
revoke all on public.jobs, public.ingest_runs, public.llm_calls from anon, authenticated;

-- jobs: read-only, active rows only
grant select on public.jobs to anon, authenticated;
drop policy if exists jobs_public_read on public.jobs;
create policy jobs_public_read on public.jobs
  for select to anon, authenticated using (is_active);

grant select on public.public_jobs to anon, authenticated;

-- ingest_runs: only non-sensitive columns of completed runs (no `errors`)
grant select (id, started_at, finished_at, status, fetched, new_posts, expired_posts)
  on public.ingest_runs to anon, authenticated;
drop policy if exists runs_public_read on public.ingest_runs;
create policy runs_public_read on public.ingest_runs
  for select to anon, authenticated using (status in ('success', 'partial'));

-- llm_calls: RLS enabled with no policies + no grants => invisible to API roles.
