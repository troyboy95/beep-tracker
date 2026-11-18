# Beep Tracker — Implementation Plan

**Goal:** A live web tool that collects 200+ real fresher job/internship posts in India from public sources (respecting ToS), deduplicates them, uses an LLM to tag each post by **role** and **city**, and serves them on a searchable page that refreshes **daily, automatically**.
**Constraints:** production-grade, minimal complexity, ~₹0 running cost, cost per 1,000 posts must be measurable (task point 3).

---

## 1. Architecture

```
GitHub Actions (cron, daily)                  Vercel (Next.js)
┌──────────────────────────────┐             ┌──────────────────────────┐
│ Python pipeline              │             │ Server components + ISR  │
│ fetch → normalize → filter → │──writes──▶  │ search / filter UI       │
│ dedup → tag (Gemini) → upsert│   Postgres  │ "last refreshed" badge   │
└──────────────────────────────┘  (Supabase) └──────────────────────────┘
                                   ▲ reads (read-only RLS) ─┘
```

| Layer | Choice | Cost |
|---|---|---|
| Frontend | Next.js (App Router) on Vercel Hobby | Free |
| Data store + search | Supabase Postgres (free tier), Postgres full-text search | Free |
| Pipeline | Python 3.12 script, run by GitHub Actions `schedule` cron | Free (public repo) |
| LLM tagging | Gemini Flash-class model (model ID via env var), JSON-schema structured output | ~cents per 1k posts |
| Sources | Public ATS job-board APIs (Greenhouse, Lever, Ashby, SmartRecruiters) + Adzuna India API for volume | Free |

### Corrections to the original plan (summary — details in CHANGELOG.md)
1. **Dropped the always-on FastAPI server on Oracle VM.** The workload is a once-a-day batch job, not a request-serving API. A VM adds patching, TLS, uptime, and idle-reclamation risk for no benefit. The IP allow-list also can't work: Vercel functions have no static egress IP on the free plan.
2. **Pipeline stays in Python**, so the reasons you picked FastAPI (LLM SDKs, data wrangling) still hold. It just runs as a scheduled job instead of a server.
3. **Postgres as the integration point** between pipeline and site. It handles dedup constraints, full-text search, and run history, and it decouples data refresh from frontend deploys.
4. **Greenhouse-only won't reach 200 India-fresher posts.** ATS boards are company-by-company, and most posts are for experienced hires. Add Lever, Ashby and SmartRecruiters (same pattern) plus Adzuna's official India API for volume. No scraping of LinkedIn, Naukri or Internshala (their ToS forbid it).
5. **LLM: pin the model by env var, use structured output with enums, batch posts per call, and only tag new or changed posts** (cached by content hash). Log token usage per run so cost per 1k posts comes straight from the data.

---

## 2. Repo layout

```
/web                 Next.js app
/pipeline            Python: sources/, normalize.py, dedup.py, tagger.py, db.py, run.py
/db/schema.sql       tables, indexes, RLS policies
/eval                sample_for_review.py, labels.csv, accuracy report (point 3)
/.github/workflows   daily-refresh.yml, ci.yml
IMPLEMENTATION_PLAN.md  CHANGELOG.md  PROMPT_LOG.md  README.md  SOURCES.md
```

## 3. Data model (Postgres)

- `jobs`: `id`, `source`, `external_id`, `url`, `title`, `company`, `location_raw`, `description` (trimmed), `posted_at`, `first_seen_at`, `last_seen_at`, `is_active`, `content_hash`, `dedup_key`, `role`, `city`, `is_fresher`, `tag_confidence`, `tag_model`, `tagged_at`, `search_tsv` (generated)
  - `UNIQUE(source, external_id)` for exact dedup; index on `dedup_key` for cross-source dedup; GIN on `search_tsv`; btree on `(role, city)`.
- `ingest_runs`: `id`, `started_at`, `finished_at`, `status`, `fetched`, `new`, `deduped`, `tagged`, `input_tokens`, `output_tokens`, `est_cost_usd`, `errors` (jsonb). The token and cost fields are roll-ups of `llm_calls`.
- `llm_calls` (**LLM ledger**, append-only, one row per API call including retries):
  - Identity: `id`, `run_id` → `ingest_runs`, `created_at`, `model`, `prompt_version`, `prompt_hash`
  - Payload: `job_ids` (array), `request` (jsonb: system prompt ref + the exact post inputs sent), `response_raw` (text, verbatim model output), `parsed_ok`, `validation_errors` (jsonb)
  - Usage: `input_tokens`, `output_tokens`, `latency_ms`, `cost_usd` (computed from a pricing table in config at call time)
  - Status: `attempt`, `retry_of`, `error`
  - `jobs.tag_call_id` → `llm_calls.id` links each tag to the exact call that produced it.
- RLS: `anon` role gets `SELECT` on active jobs and run summary only, and has **no access** to `llm_calls`. Writes go through the service key, which only the pipeline has (as a GH Actions secret).
- Ledger size: about 20 KB per call × ~20 calls a day ≈ 0.5 MB a day, well inside the 500 MB free tier. Optional retention: clear `request`/`response_raw` older than 180 days but keep the usage columns.

## 4. Pipeline flow (`pipeline/run.py`)

1. **Fetch** each source adapter → common `RawPost` model. Per-source timeout, retry with backoff, polite rate limit, and a descriptive User-Agent. One source failing never fails the whole run.
2. **Normalize**: clean HTML → text, trim the description to ~1.5k chars, canonicalize URL, parse dates.
3. **India filter** (deterministic): location contains India/Indian city list/"Remote – India".
4. **Fresher pre-filter** (cheap heuristics): intern/trainee/graduate/fresher/entry/junior/associate/"0–1 yrs". Drop obvious senior roles (senior/lead/manager/staff/principal). The LLM confirms `is_fresher` in the next step.
5. **Dedup**: exact by `(source, external_id)`. Cross-source by `dedup_key = hash(norm(company) + norm(title) + norm(city))`.
6. **Tag** only rows with new or changed `content_hash`. Batch ~10–20 posts per call. JSON schema output: `role` (fixed enum taxonomy, e.g. SWE, Data/ML, Product, Design, QA, DevOps/Cloud, Sales, Marketing, Ops, Finance, HR, Support, Other), `city` (canonical enum: Bengaluru, Mumbai, Delhi NCR, Hyderabad, Pune, Chennai, Kolkata, Ahmedabad, …, Remote, Multiple, Other), `is_fresher`, `confidence`. Validate with Pydantic. Retry invalid items once, then fall back to `Other`. **Every call, including failures and retries, is written to `llm_calls` before its result is used.** The system prompt lives in code under a version string (`prompt_version`) and its hash is recorded with each call.
7. **Upsert** jobs with `tag_call_id`. Mark posts not seen in this run as `is_active=false` (soft expire). Write the `ingest_runs` row, with token and cost totals rolled up from `llm_calls`.

## 5. Frontend (`/web`)

- Single page: search box (full text), filters (role, city, source, job/internship), sort by newest, pagination, outbound "Apply" links.
- Server component queries Supabase. `revalidate` ≈ 1h, plus an on-demand revalidate hook that the pipeline calls after each run.
- Header badge: "N posts · last refreshed <time>" from `ingest_runs`, so the daily refresh is visible.
- Empty, loading and error states. Mobile-friendly.

---

## 6. Checklist

### Phase 0 — Setup
- [x] `git init`, `.gitignore` (incl. `.claude-manifest*.json`, `.env*`)
- [ ] Public GitHub repo created and pushed *(user)*
- [x] `db/schema.sql` written: tables, `public_jobs` dedup view, RLS/grants, append-only ledger trigger
- [ ] Supabase project created; `db/schema.sql` applied; RLS verified with publishable key *(user creds)*
- [ ] Gemini API key; confirm current Flash-Lite model ID and pricing → `.env` *(user creds)*
- [ ] Adzuna API key (India) *(user creds)*
- [x] `SOURCES.md`: each source, endpoint, ToS note, rate limit (company list in Phase 1)
- [x] `.env.example`, `README.md`, pipeline skeleton (`pyproject.toml`, typed `config.py`, `RawPost`/`Source` contract)
- [x] `python -m beep.doctor` checks the credentials and connectivity; lint + tests pass
- [ ] `beep.doctor` all green *(after creds)*

### Phase 1 — Pipeline
- [x] `RawPost` model + source adapter interface (with title pre-check hook)
- [x] Adapters: Greenhouse, Lever, Ashby, SmartRecruiters; 68 boards verified by `scripts/probe_boards.py` (Adzuna dropped)
- [x] Normalize + India filter + 0–2 yrs eligibility pre-filter (title + description)
- [x] Dedup: exact `(source, external_id)` + `dedup_key` view
- [x] Gemini tagger: batching, JSON schema, Pydantic validation, bounded retries + deferred pass, token accounting, prompt v2
- [x] LLM ledger: `llm_calls` write on every call (success/failure/retry), `prompt_version` + hash, `jobs.tag_call_id` link
- [x] Ledger CLI: `python -m beep.ledger --run/--job/--call/--cost`
- [x] DB upsert, per-board soft-expire, `ingest_runs` logging, versioned migrations (`beep.migrate`)
- [x] Full run → **≥200 active fresher posts in India** in `public_jobs` (277 on 2026-11-18)
- [x] Durable tagging queue (pending/done/failed, backoff, 429 `retryDelay`, daily-quota stop, circuit breaker) + `--tag-only` drain mode
- [x] Unit tests: normalize, filters, dedup key, tagger response parsing (32 passing)

### Phase 2 — Automation
- [ ] `daily-refresh.yml`: cron (daily, IST-friendly), `workflow_dispatch` for manual runs, secrets, concurrency guard, timeout
- [ ] `tag-drain.yml`: `python -m beep.run --tag-only` every ~4 h (same concurrency group, so it never overlaps the daily run)
- [ ] Failure notification (GH Actions email default) and non-zero exit if total fetched = 0
- [ ] Trigger Vercel on-demand revalidation at the end of the run
- [ ] `ci.yml`: lint + tests on PR

### Phase 3 — Frontend
- [ ] Next.js app scaffold, `supabase-js` server client (publishable key, read-only) with types from `supabase gen types` (no ORM, see CHANGELOG)
- [ ] Search + filters + pagination via URL params
- [ ] Last-refreshed badge, empty/error states, responsive layout
- [ ] Deploy to Vercel; env vars set; revalidate secret

### Phase 4 — Hardening & docs
- [ ] Verify one automated cron run end-to-end in production
- [ ] README: architecture diagram, setup, run locally, costs
- [ ] CHANGELOG.md kept current; PROMPT_LOG.md updated each session
- [ ] "What broke & how we fixed it" notes captured in CHANGELOG as they happen (video material)

### Phase 5 — Evaluation (plan only, not executed now; task point 3)
- [ ] `eval/sample_for_review.py`: random stratified sample of 50 tagged posts → CSV
- [ ] Hand-label role/city/is_fresher → compute per-field accuracy; for each mismatch, pull the ledger entry (`tag_call_id`) to show the model's raw input and output
- [ ] Cost per 1,000 posts = Σ(`llm_calls.cost_usd`, retries included) / count(distinct tagged jobs) × 1000, at paid-tier prices (+ infra = $0)

---

## 7. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Fewer than 200 India fresher posts | Expand curated ATS company list; Adzuna query terms (`intern`, `fresher`, `graduate`, `trainee`); keep inactive posts out of the count |
| GH Actions cron delay / auto-disable after 60 days of repo inactivity | Acceptable for demo; `workflow_dispatch` backup; keep-alive note in README |
| Supabase free project pauses after 7 days idle | Daily pipeline writes keep it active |
| LLM model deprecation | Model ID via env var; schema-validated output is model-agnostic |
| Source API change | Per-source isolation, errors recorded in `ingest_runs.errors` |
| Vercel Hobby is non-commercial | Fine for an assessment/demo |
