# Beep Tracker

A live, searchable list of **fresher jobs and internships in India**, built from public job-board APIs. Posts are deduplicated, tagged by **role** and **city** with an LLM, and refreshed automatically every day.

> Work in progress. See [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) for status and [`CHANGELOG.md`](CHANGELOG.md) for design decisions.

## The task

1. **Build it.** A live web tool that collects 200+ real fresher job/internship posts in India from public sources (respecting each site's terms), removes duplicates, uses an LLM to tag each post by role and city, and shows them on a searchable page that refreshes daily on its own.
2. **Explain it.** Architecture, what broke and how it was fixed.
3. **Put a number on it.** Hand-check 50 posts for tagging accuracy, and report the cost per 1,000 posts.

## Architecture

```
GitHub Actions (daily cron) ── Python pipeline ──▶ Supabase Postgres ◀── Next.js on Vercel
  fetch → filter → dedup → Gemini tag → upsert       jobs · ingest_runs · llm_calls (ledger)
```

| Path | What |
|---|---|
| `pipeline/` | Python ingestion pipeline (`beep` package) |
| `db/migrations/` | Versioned schema: tables, dedup view, RLS, append-only LLM ledger, tag queue |
| `web/` | Next.js 16 frontend (see [`web/README.md`](web/README.md)) |
| `SOURCES.md` | Data sources and their terms |

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

## Running the pipeline

```bash
python -m beep.run --dry-run        # fetch + filter only, no DB/LLM
python -m beep.run                  # full: fetch → filter → upsert → expire → drain tag queue
python -m beep.run --tag-only       # drain the LLM tagging queue only
python -m beep.ledger --cost        # cost per 1,000 posts from the LLM ledger
python -m beep.ledger --job 123     # exact LLM input/output behind a post's tags
```

## Deploying the web app (Vercel)

The repo deploys with [Vercel Services](https://vercel.com/docs/services) via [`vercel.json`](vercel.json): one public service, `web` (Next.js, `web/`), serving every path. The pipeline is **not** a Vercel service. It's a batch job that GitHub Actions runs, and it reaches the site only through the public `/api/revalidate` endpoint, so no service bindings are needed.

1. Vercel → *Add New Project* → import `troyboy95/beep-tracker`. Leave **Root Directory** as the repo root (`vercel.json` lives there and points the `web` service at `web/`).
2. Add these environment variables: `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` and `REVALIDATE_SECRET`.
3. Deploy. Then, in GitHub Actions settings, set the variable `REVALIDATE_URL=https://<app>.vercel.app/api/revalidate` and the secret `REVALIDATE_SECRET` (same value as in Vercel).

## Automation (GitHub Actions)

| Workflow | When | What |
|---|---|---|
| `pipeline.yml` | Daily 02:30 UTC (08:00 IST) | Migrations + full refresh (fetch → filter → upsert → expire → tag) |
| `pipeline.yml` | 06:45, 10:45, 14:45, 18:45, 22:45 UTC | `--tag-only` drain of the LLM tagging queue |
| `pipeline.yml` | Manual (*Run workflow*) | Choose `full` or `tag_only` |
| `ci.yml` | Push to `main`, PRs | ruff + pytest |

All pipeline runs share one concurrency group, so they never overlap.

Repo settings → *Secrets and variables* → *Actions*:

| Kind | Name | Value |
|---|---|---|
| Secret | `DATABASE_URL` | Supabase **session pooler** connection string |
| Secret | `GEMINI_API_KEY` | Google AI Studio key |
| Secret | `REVALIDATE_SECRET` | Same random string as in Vercel *(after Phase 3)* |
| Variable | `GEMINI_MODEL` | e.g. `gemini-3.1-flash-lite` |
| Variable | `GEMINI_PRICE_INPUT_PER_M` / `GEMINI_PRICE_OUTPUT_PER_M` | USD per 1M tokens (for cost reporting) |
| Variable | `HTTP_USER_AGENT` | `BeepTracker/0.1 (+https://github.com/troyboy95/beep-tracker)` |
| Variable | `REVALIDATE_URL` | `https://<app>.vercel.app/api/revalidate` *(after Phase 3)* |

> GitHub may delay scheduled runs at busy times, and it disables schedules on public repos after 60 days without activity. Use *Run workflow* to trigger manually.

Tagging is a durable queue in Postgres (`jobs.tag_status`). Rate limits or provider outages only delay tags and never lose them: failed items back off and are picked up by the next run.

## Cost

Every service runs on a free tier: Vercel Hobby, Supabase Free, GitHub Actions on a public repo, the Gemini free tier and an Adzuna free key. The reported cost per 1,000 posts is calculated at **paid-tier** LLM prices from the `llm_calls` ledger.
