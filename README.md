# Beep Tracker

A live, searchable list of **fresher jobs and internships in India** (0–2 years of experience), built from public job-board APIs. Posts are deduplicated, tagged by **role** and **city** with an LLM, and refreshed automatically every day.

**Live:** https://beep-tracker.vercel.app · **Design decisions:** [`CHANGELOG.md`](CHANGELOG.md) · **Plan / checklist:** [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) · **Accuracy:** [`eval/`](eval/README.md)

| | |
|---|---|
| Sources | 68 company boards on Greenhouse, Lever, Ashby and SmartRecruiters (official public APIs, see [`SOURCES.md`](SOURCES.md)) |
| Volume | ~4,100 posts fetched per run → ~450 active India posts within 0–2 yrs → **~280 public listings** after dedup |
| Tagging accuracy (50-post human-confirmed check) | all four fields **84%** strict / **94%** lenient; city **100%**; fresher precision **96%** |
| Cost | **$0.17 per 1,000 posts** (LLM, paid-tier prices) · **$0 actually billed** (all free tiers) |

## How it works

```
GitHub Actions (cron) ── Python pipeline ──────────────► Supabase Postgres ◄── Next.js on Vercel ◄── visitors
  migrate → fetch 68 boards → India + 0–2 yrs filter        jobs · ingest_runs        cached reads,
  → upsert → expire → tag queue (Gemini) → revalidate ──►  llm_calls (ledger)        /api/revalidate
```

1. **Collect.** GitHub Actions runs `python -m beep.run` daily, fetching every board's public API with a polite User-Agent, a throttle per site and retries. Posts outside India, posts with senior/managerial titles, and posts whose stated minimum experience is above 2 years are dropped deterministically.
2. **Store and dedupe.** Posts are upserted by `(source, external_id)`. The `public_jobs` view shows one row per `company + title + location` across sources. Posts that disappear from a board are marked inactive, only for boards that fetched successfully.
3. **Tag.** New or changed posts go through a durable queue in Postgres to Gemini, 15 per call. The output is constrained to fixed role/city/job-type lists and validated with Pydantic. Every call, failures and retries included, is written first to the append-only `llm_calls` ledger. If the location names exactly one known city, a deterministic rule sets the city (`city_source = rule`). Rate limits and outages only delay tags; nothing is lost.
4. **Refresh the site.** After a run that changed data, the pipeline calls `POST /api/revalidate`, which expires the site's cached data. Pages are served from Next.js 16's cache (Cache Components / Partial Prerendering). The database is queried roughly once an hour per unique filter, not once per visitor.
5. **Browse.** Full-text search (fires while typing, ≥ 4 characters, debounced), role/city filters with counts, and Jobs/Internships. Everything lives in the URL, works without JavaScript, and links to the employer's own posting.

### Authentication

| Connection | How it's authenticated | Where the credential lives |
|---|---|---|
| Pipeline → job boards | None (public APIs) | — |
| Pipeline → Postgres | Database password over TLS (Supabase session pooler, IPv4) | GitHub secret `DATABASE_URL` |
| Pipeline → Gemini | API key | GitHub secret `GEMINI_API_KEY` |
| Pipeline → site cache | `Authorization: Bearer` shared secret, constant-time compare | GitHub secret + Vercel env `REVALIDATE_SECRET` |
| Site → Postgres | Supabase **publishable** key (`anon` role), server-side only. Row-level security allows read-only access to active jobs, the dedup view and non-sensitive run columns; the ledger is invisible | Vercel env `SUPABASE_PUBLISHABLE_KEY` |
| Visitor → site | None (public, read-only) | — |

## Cost

All numbers come from the `llm_calls` ledger (`python -m beep.ledger --cost`) and are priced at **paid-tier** rates, so they show the real unit cost even though everything ran on free tiers.

### LLM (Gemini `gemini-3.1-flash-lite`, $0.25 / M input, $1.50 / M output tokens)

| Measure | Value |
|---|---|
| Tokens per post | ~281 input / ~67 output (title, company, location, hints + a ~1.4k-char excerpt of the experience and location sentences) |
| **Cost per 1,000 posts, tagging only** | **$0.170** |
| Cost per 1,000 posts, all-in (retries + re-tags after prompt changes) | $0.180 |
| Calls to date | 66, of which 29 failed with 503/429 (not billed) |
| Total LLM spend to date (493 posts tagged) | **$0.089** at paid prices · $0 billed |
| Initial backfill (~450 posts) | ~$0.08 |
| Steady state (~20 new or edited posts per day) | ~$0.0035/day ≈ **$0.11/month** at paid prices |

Cost stays low by design: deterministic filters remove ~50% of India posts before the LLM (907 → ~450); 15 posts share one prompt; only new or changed posts (by content hash) are tagged; the city rule and senior-title rules need no LLM calls; failed calls are free.

### Infrastructure

| Service | Plan | Usage | Cost |
|---|---|---|---|
| Vercel | Hobby | One Next.js service; cached pages | $0 |
| Supabase Postgres | Free | 20 MB of 500 MB; daily writes keep the project from pausing | $0 |
| GitHub Actions | Public repo | 1 full run (~5 min) + 5 drains per day, CI on push | $0 |
| Gemini API | Free tier | ~2 calls/day in steady state | $0 |
| **Total** | | | **$0/month** (≈ $0.11/month if the LLM were on paid tier) |

At 100× the volume (~2,000 new posts per day), the LLM would cost about $0.34/day; the rest would still fit the free tiers except possibly Supabase storage over time.

## Repository

| Path | What |
|---|---|
| `pipeline/` | Python ingestion pipeline (`beep` package): sources, filters, tag queue, ledger, migrations, tests |
| `db/migrations/` | Versioned schema: tables, dedup view, RLS, append-only ledger, tag queue, `city_source` |
| `web/` | Next.js 16 frontend (see [`web/README.md`](web/README.md)) |
| `eval/` | 50-post tagging evaluation: sampling, labels, scoring, reports |
| `vercel.json` | Vercel Services config: one public `web` service |
| `.github/workflows/` | `pipeline.yml` (scheduled pipeline), `ci.yml` (lint + tests) |

## Local setup

```bash
cp .env.example .env               # fill in values (see comments inside)

cd pipeline
python -m venv .venv
.venv/Scripts/activate              # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -e ".[dev]"
python -m beep.migrate              # apply db/migrations/*.sql
python -m beep.doctor               # checks env vars, DB schema, Gemini model
pytest
```

Web app: see [`web/README.md`](web/README.md) (`npm install && npm run dev`, with `web/.env.local`).

## Running the pipeline

```bash
python -m beep.run --dry-run        # fetch + filter only, no DB/LLM
python -m beep.run                  # full: fetch → filter → upsert → expire → drain tag queue
python -m beep.run --tag-only       # drain the LLM tagging queue only
python -m beep.ledger --cost        # cost per 1,000 posts from the LLM ledger
python -m beep.ledger --job 123     # exact LLM input/output behind a post's tags
```

Don't run the pipeline locally against production while a GitHub run is active: local runs are outside the workflow's concurrency group.

## Evaluation

[`eval/README.md`](eval/README.md) covers the method, results and failure analysis. In short: a seeded random sample of 50 posts (including ones the model rejected), human-confirmed gold labels, and strict/lenient accuracy with 95% confidence intervals. It reports before/after numbers for the deterministic fixes the evaluation led to (city resolver, senior-title rules).

## Deploying the web app (Vercel)

The repo deploys with [Vercel Services](https://vercel.com/docs/services) via [`vercel.json`](vercel.json): one public service, `web` (Next.js, `web/`), serving every path. The pipeline is **not** a Vercel service. It's a batch job that GitHub Actions runs, and it reaches the site only through the public `/api/revalidate` endpoint, so no service bindings are needed.

1. Vercel → *Add New Project* → import `troyboy95/beep-tracker`. Leave **Root Directory** as the repo root.
2. Add these environment variables: `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` and `REVALIDATE_SECRET`.
3. Deploy. Then, in GitHub Actions settings, set the variable `REVALIDATE_URL=https://<app>.vercel.app/api/revalidate` and the secret `REVALIDATE_SECRET` (same value as in Vercel).

## Automation (GitHub Actions)

| Workflow | When | What |
|---|---|---|
| `pipeline.yml` | Daily 02:30 UTC (08:00 IST) | Migrations + full refresh |
| `pipeline.yml` | 06:45, 10:45, 14:45, 18:45, 22:45 UTC | Migrations + `--tag-only` drain of the tagging queue |
| `pipeline.yml` | Manual (*Run workflow*) | Choose `full` or `tag_only` |
| `ci.yml` | Push to `main`, PRs | Pipeline: ruff + pytest · Web: ESLint + typecheck |

All pipeline runs share one concurrency group, so they never overlap, and no database locks are needed. Each run writes a summary table to the Actions page.

Repo settings → *Secrets and variables* → *Actions*:

| Kind | Name | Value |
|---|---|---|
| Secret | `DATABASE_URL` | Supabase **session pooler** connection string |
| Secret | `GEMINI_API_KEY` | Google AI Studio key |
| Secret | `REVALIDATE_SECRET` | Same random string as in Vercel |
| Variable | `GEMINI_MODEL` | e.g. `gemini-3.1-flash-lite` |
| Variable | `GEMINI_PRICE_INPUT_PER_M` / `GEMINI_PRICE_OUTPUT_PER_M` | USD per 1M tokens (for cost reporting) |
| Variable | `HTTP_USER_AGENT` | `BeepTracker/0.1 (+https://github.com/troyboy95/beep-tracker)` |
| Variable | `REVALIDATE_URL` | `https://beep-tracker.vercel.app/api/revalidate` |

> GitHub may delay scheduled runs at busy times (observed: up to ~8 h), and it disables schedules on public repos after 60 days without activity. Use *Run workflow* to trigger manually.
