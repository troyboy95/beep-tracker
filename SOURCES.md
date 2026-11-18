# Data Sources

Only official, public, documented job-board APIs are used. No HTML scraping, no login-walled sites, and no aggregators.
All requests send a descriptive `User-Agent` (`HTTP_USER_AGENT`), use timeouts and retries with exponential backoff (on 429/5xx), and are throttled per host (`beep/http.py`).

| Source | Endpoint | Auth | Terms / notes |
|---|---|---|---|
| Greenhouse Job Board API | `GET https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true` | None | Public API that companies use to embed their own job boards. Read-only. |
| Lever Postings API | `GET https://api.lever.co/v0/postings/{company}?mode=json` | None | Public postings API for embedding job lists. |
| Ashby Job Posting API | `GET https://api.ashbyhq.com/posting-api/job-board/{board}` | None | Public job-board API. Unlisted posts (`isListed=false`) are skipped. |
| SmartRecruiters Posting API | `GET https://api.smartrecruiters.com/v1/companies/{company}/postings?country=in` and `/postings/{id}` | None | Public Posting API. India filter applied server-side. The detail endpoint is called only for posts whose title passes the fresher pre-check, to keep request volume low. |

Every post links back to the original posting (`url`). Applications always happen on the employer's site.

## Explicitly excluded

| Site | Reason |
|---|---|
| LinkedIn, Naukri, Indeed, Internshala, Glassdoor | Terms of service prohibit automated scraping; no public listing API |
| Adzuna API | Considered for volume; dropped by product decision (2026-11-18). ATS boards with the 0–2 years rule give enough volume. |

## Curated company boards

ATS sources are queried per company: [`pipeline/beep/sources/companies.toml`](pipeline/beep/sources/companies.toml). Boards were discovered and verified with [`pipeline/scripts/probe_boards.py`](pipeline/scripts/probe_boards.py) on 2026-11-18. That run probed ~400 candidate tokens and found 68 boards with India posts.

| Snapshot (2026-11-18) | Count |
|---|---|
| Boards | 68 (40 Greenhouse, 9 Lever, 7 Ashby, 12 SmartRecruiters) |
| Posts fetched (after title pre-check) | 4,122 |
| India-located | 907 |
| Passed 0–2 yrs eligibility pre-filter | ~450 |

> Terms checked: 2026-11-18 (public, unauthenticated, documented endpoints intended for third-party display of job listings).
