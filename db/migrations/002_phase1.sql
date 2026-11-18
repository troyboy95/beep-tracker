-- Phase 1: board tracking (safe per-board expiry), eligibility audit columns,
-- exclude non-India tags from the public view.

alter table public.jobs add column if not exists board            text;
alter table public.jobs add column if not exists hints            text;
alter table public.jobs add column if not exists min_years_hint   smallint;
alter table public.jobs add column if not exists prefilter_reason text
  check (prefilter_reason in ('explicit', 'le2', 'no_signal'));

update public.jobs set board = '' where board is null;
alter table public.jobs alter column board set not null;

create index if not exists jobs_source_board_idx on public.jobs (source, board) where is_active;

create or replace view public.public_jobs
with (security_invoker = true) as
select distinct on (dedup_key)
  id, source, url, title, company, location_raw, posted_at, first_seen_at,
  role, city, job_type, search_tsv
from public.jobs
where is_active
  and is_fresher is true
  and tagged_at is not null
  and city is distinct from 'Outside India'
order by dedup_key, first_seen_at, id;

grant select on public.public_jobs to anon, authenticated;
