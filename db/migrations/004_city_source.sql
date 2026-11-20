-- Where the final city tag came from: a deterministic rule on location_raw, or the LLM.
-- The ledger (llm_calls.response_raw) always keeps the LLM's original answer.
alter table public.jobs add column if not exists city_source text
  check (city_source in ('rule', 'llm'));

update public.jobs set city_source = 'llm' where tagged_at is not null and city_source is null;
