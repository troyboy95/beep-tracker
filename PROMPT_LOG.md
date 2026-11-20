# Prompt Log

Verbatim log of prompts given to the AI assistant (Claude Code) during development, kept for the demo. Append new sessions at the bottom.

---

## Session fb377eb2 — 2026-11-17 (device: LAPTOP-CUUHKO8Q)

### Prompt 1
> File has the task that we have to accomplish. Ignore point 3 (for execution purpose, but consider for planning). Here's what I've planned for its implementation:
> Frontend - We'll use next.js, deploy on vercel
> Backend - FastAPI (for easy LLM calls & data integration, could have picked Node.js + Express too), deploy on Oracle Cloud free VM via public IP & selective IP allow-list.
> LLM - Gemini 2.5 flash for a tagging
> Job boards public API - like Greenhouse, etc.
>
> Goal is to complete the task, ensure prod level implementation without unnecessary complexity, and least possible cost (as per point 3). Review the plan, suggest corrections as a senior engineer and then create an IMPLEMENTATION_PLAN.md file consisting a brief plan, alsow works as checklist.
> We'll also need to keep prompt logs for this session, for the demo, so create a log file. Furthermoe, as a standard parctice create a CHANGELOG.md, which consists of the all design decisions & basic context. Follow a tabular rule with cols - What, When, Why, Where

**Outcome:** Reviewed the plan. Replaced the always-on FastAPI server on the Oracle VM with a GitHub Actions cron Python pipeline writing to Supabase Postgres. Dropped the IP allow-list (not workable with Vercel). Broadened sources beyond Greenhouse. Hardened the LLM tagging approach. Created `IMPLEMENTATION_PLAN.md`, `CHANGELOG.md`, `PROMPT_LOG.md` and `.gitignore`.

### Prompt 2
> I also suggest that we keep track record of the LLM calls, input & output to the LLM, like a ledger

**Outcome:** Added an append-only `llm_calls` ledger table: exact request and response, model, prompt version/hash, tokens, latency, cost, retries and errors. Linked each job to its tagging call via `jobs.tag_call_id`. Kept it hidden from the public via RLS. Added a ledger CLI to the checklist. Point-3 cost and accuracy checks now come from the ledger. Updated `IMPLEMENTATION_PLAN.md` and `CHANGELOG.md`.

### Prompt 3
> start phase 0, and at the end of the scaffold, notify me with creds reqd from Supaase & elsewhere. Keep an .env.example

**Outcome (in progress):** `git init` done. Wrote `db/schema.sql` (tables, `public_jobs` dedup view, RLS, append-only ledger trigger), `.env.example`, `SOURCES.md`, and the Python pipeline skeleton (`pipeline/pyproject.toml`, `beep/config.py`, `beep/sources/base.py`, `companies.toml`). Interrupted by Prompt 4.

### Prompt 4
> Wouldn't it be advisable to use ORM, drizzle is good

**Outcome:** Reviewed ORM trade-offs. Drizzle is TypeScript-only, so it can't serve the Python pipeline. Recommended keeping SQL as the schema source of truth and optionally using Drizzle (introspected) for typed reads in `web/`. Waiting for the user's decision.

### Prompt 5
> go with A, continue phase 0

**Outcome:** Chose Option A (no ORM; `supabase-js` + generated types in web). Finished the Phase 0 scaffold: `beep.doctor` credential/connectivity checker, config tests, README, `.gitignore` update. Venv install, `ruff` and `pytest` (2 passed) all succeed. `doctor` correctly reports missing creds. Updated the checklist and changelog. Sent the user the list of required credentials.

### Prompt 6
> For free tier backup, add a retry for Gemini API due to rate limit issue. More like a queueing mechanism, to remeber which are still pending when it runs on deploy. Furthermore, why id cols across tables is int8 type? I understand ots easier for lookup, and no uuid is reqd at this stage of the project

**Outcome:** Built a durable tagging queue in Postgres (migration 003: `tag_status`/`tag_attempts`/`next_tag_at`/`last_tag_error`) and a worker (`beep/tag_queue.py`):
- honors 429 `retryDelay`
- stops when the daily quota is exhausted
- circuit breaker after 4 consecutive failing batches
- backoff for failed items; parks an item as `failed` after 3 bad outputs; transient errors never count as failures

Added a `--tag-only` drain mode. Verified on the real 503 backlog: queue 45 → 0, public listings 242 → 277. Explained the `bigint` PK choice (int4 would suffice; bigint is cheap insurance against an FK/array type migration; UUIDs unnecessary) and logged it in the CHANGELOG. Measured cost: $0.178 per 1,000 posts.

### Prompt 7
> Begin phase 2, and fix the gap with concurrency group. Locks are unnecessary here

**Outcome:**
- `pipeline.yml`: one workflow, so a single concurrency group serializes all pipeline runs (closes the double-tagging gap without DB locks).
  - Daily full refresh at 08:00 IST, with migrations.
  - `--tag-only` drains 5× a day.
  - Manual run with a mode choice.
- `ci.yml` runs ruff + pytest.
- GitHub job summary on every run.
- Fixed two CI-only issues before shipping: empty repo Variables overriding defaults (`env_ignore_empty` + test), and the editable install needed by `migrate`.
- Found and fixed UTF-8 corruption from PowerShell text edits (`doctor.py`, workflows).
- 35 tests pass; workflows parse. Listed the GitHub secrets/variables to configure.

### Prompt 8
> Changes pushed, start phase 3 - frontend. Keep the UI monotonous, no multi-color. Sleek, elegant. Check plans/frontend-ref.jpg as ref img

**Outcome:** Built `web/` on Next.js 16.4.6 (Cache Components + Partial Prerendering; checked APIs against the bundled docs).
- Data layer: `'use cache'` + `cacheTag('jobs')`; `/api/revalidate` endpoint; types generated from the DB.
- Features: full-text search, role/city filters with counts, Jobs/Internships segment, pagination. All URL-driven and working without JS.
- Monochrome design after the reference: two-weight Albert Sans headline, Source Serif 4 prose, black chip reused as the "Updated" timestamp, grey filter band, heartbeat logo. Dark mode inverts the same scale.
- Verified with headless screenshots at 1440px and 400px, light and dark. Fixed three issues they caught: chip overflow, logo invisible under reduced motion, long-title overflow.
- Checked the revalidate endpoint auth (401/401/200/405).
- CI gains a web lint + typecheck job.
- Vercel deploy steps documented for the user.

### Prompt 9
> Configure this repository to deploy on Vercel as a project with multiple services. *(Vercel-suggested `vercel.json` with `pipeline` (python) + `web` (nextjs) services and a catch-all rewrite; asked to add bindings, update code to use them, and confirm service names, public paths and bindings.)*

**Outcome:** Checked against the Vercel Services docs. Recommended against making `pipeline` a service: it's a batch CLI with no HTTP entrypoint, run by GitHub Actions within duration limits Hobby can't meet. Found no Vercel-internal service calls, so no bindings and no code changes. Wrote `vercel.json` with a single public `web` service and asked the user to confirm.

### Prompt 10
> Looks alright, proceed with no bindings

**Outcome:** Finalized `vercel.json` (one public `web` service). Updated the README deploy steps (project root = repo root, not `web`), CHANGELOG and plan.

### Prompt 11
> Ran one full workflow, still seeing 276 openings

**Outcome:** Traced the run across GitHub Actions (success), the DB (`ingest_runs` #4: manual/full/success, 0 new, 1 updated, 1 tagged) and the live page (stamp updated to the run's finish time without a redeploy). This confirmed the full prod chain, including revalidation. Explained 277 → 276: one Paytm "Team Leader" post was edited upstream, re-tagged, and is now correctly non-fresher. That surfaced a pre-filter gap ("Leader" isn't matched as a senior title). Re-ran the UI interaction suite against prod: all behaviour checks pass.

### Prompt 12
> update readme, with cost

**Outcome:** Rewrote `README.md`: live URL, at-a-glance table (sources, volume, accuracy, cost), how it works, authentication table. The cost section was pulled fresh from the ledger and run history: $0.170 per 1,000 posts tagging-only / $0.180 all-in, ~281/67 tokens per post, $0.089 total to date, steady state ≈ $0.11/month at paid prices. Infra is $0 on free tiers (Supabase 20 MB of 500 MB). Kept the user's removal of the task section; removed stale notes; documented the web CI job.
