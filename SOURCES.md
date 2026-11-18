# Data Sources

Only official, public, documented APIs are used. No HTML scraping, no login-walled sites.
All requests send a descriptive `User-Agent` (`HTTP_USER_AGENT`), use timeouts and retries with backoff, and are rate-limited to roughly 1 request/second per host.

| Source | Endpoint | Auth | Terms / notes | Why included |
|---|---|---|---|---|
| Greenhouse Job Board API | `GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true` | None | Public, documented API meant for companies' own job boards to embed listings. Read-only GETs. | Many India-hiring tech companies use it |
| Lever Postings API | `GET https://api.lever.co/v0/postings/{company}?mode=json` | None | Public postings API meant for embedding job lists. | Same pattern, more companies |
| Ashby Job Posting API | `GET https://api.ashbyhq.com/posting-api/job-board/{board}` | None | Public job-board API. | Startups hiring in India |
| SmartRecruiters Posting API | `GET https://api.smartrecruiters.com/v1/companies/{company}/postings?country=in` | None | Public postings API; supports country filter. | Large enterprises with India hiring |
| Adzuna API (India) | `GET https://api.adzuna.com/v1/api/jobs/in/search/{page}?app_id&app_key&what=…` | App ID + key (free) | Official aggregator API. **Attribution required in the UI** ("Jobs by Adzuna" link). Keep within free-tier call limits. | Volume: entry-level / intern / fresher queries across India |

## Explicitly excluded

| Site | Reason |
|---|---|
| LinkedIn, Naukri, Indeed, Internshala, Glassdoor | Terms of service prohibit automated scraping, and there is no public API for listings |

## Curated company lists

ATS sources are queried per company. The board tokens live in `pipeline/sources/companies.toml` and are verified in Phase 1: each must return 200, and the company must have India locations. Each entry records why the company was included.

> Before going live, re-check each provider's current terms. Record the date checked here: _pending (Phase 1)_.
