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
| `db/schema.sql` | Schema, dedup view, RLS, append-only LLM ledger |
| `web/` | Next.js frontend *(Phase 3)* |
| `SOURCES.md` | Data sources and their terms |

## Local setup

```bash
cp .env.example .env               # fill in values (see comments inside)
# Apply db/schema.sql in the Supabase SQL Editor

cd pipeline
python -m venv .venv
.venv/Scripts/activate              # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -e ".[dev]"
python -m beep.doctor               # checks env vars, DB schema, Gemini model, Adzuna key
pytest
```

## Cost

Every service runs on a free tier: Vercel Hobby, Supabase Free, GitHub Actions on a public repo, the Gemini free tier and an Adzuna free key. The reported cost per 1,000 posts is calculated at **paid-tier** LLM prices from the `llm_calls` ledger.
