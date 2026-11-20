# Tagging accuracy: 50-post hand check (after fixes 1–3)

- Sample: 50 posts drawn at random (seed `20261120`) from **454 active tagged posts** on 2026-11-20. This includes posts the model *rejected* as non-fresher, so `is_fresher` is tested both ways.
- Reviewer: human-confirmed 2026-11-20 (first pass: claude). Gold labels follow the same written rules as the prompt (fresher = minimum required experience ≤ 2 yrs, or none stated and not a senior/managerial role).
- *Strict* = exact match. *Lenient* also accepts a different-but-defensible label the reviewer marked `alt_ok`.

## Accuracy per field

| Field | Strict | Lenient |
|---|---|---|
| role | 45/50 = **90%** (95% CI 79%–96%) | 50/50 = **100%** (95% CI 93%–100%) |
| city | 50/50 = **100%** (95% CI 93%–100%) | 50/50 = **100%** (95% CI 93%–100%) |
| job_type | 50/50 = **100%** (95% CI 93%–100%) | 50/50 = **100%** (95% CI 93%–100%) |
| is_fresher | 47/50 = **94%** (95% CI 84%–98%) | 47/50 = **94%** (95% CI 84%–98%) |
| **all 4 fields** | 42/50 = **84%** (95% CI 71%–92%) | 47/50 = **94%** (95% CI 84%–98%) |

## What users see: the fresher filter

- **Precision** (shown posts that really are fresher-eligible): 26/27 = **96%** (95% CI 82%–99%)
- **Recall** (fresher-eligible posts that get shown): 26/28 = **93%** (95% CI 77%–98%)

## Every disagreement

| id | Post | Field | Model | Gold | Defensible? | Note |
|---|---|---|---|---|---|---|
| 37 | MongoDB: Early Talent Recruiter | is_fresher | True | False | no | Needs 4+ yrs recruiting; model swayed by 'early talent / interns / graduates' wording |
| 58 | Pure Storage: Workday Analyst | role | Operations & Supply Chain | DevOps, Cloud & IT | yes | Workday HCM configuration = HR/IT systems; Operations is a stretch but defensible. No years stated → fresher per rule |
| 102 | Glance: Consultant - AI Governance Specialist | role | Consulting & Strategy | Legal & Compliance | yes | AI governance/risk; 'Consultant' title makes Consulting defensible |
| 211 | Paytm: Project Coordinator - CSR - 6 months Contract | is_fresher | False | True | no | 2–4 yrs → minimum 2 → fresher under our 0–2 rule; model said no |
| 305 | Swiggy: Executive - Video Editor | role | Design | Marketing & Content | yes | Video editor for a food-media brand; Design defensible |
| 357 | Bosch: 2026/02: HW Developer for Electronic Control Unit | role | Core Engineering | Hardware & Embedded | yes | Power-electronics HW for an ECU; Core Engineering (electrical) defensible |
| 423 | Bosch: EDR Function Responsible for BEG Airbag projects | role | Software Engineering | Hardware & Embedded | yes | Airbag ECU software requirements = embedded; Software Engineering defensible |
| 440 | Bosch: Logistics System Analyst & Rollout Engineer | is_fresher | False | True | no | No years stated, not a senior title → fresher by rule; borderline ('proven experience', project mgmt) |

## Cost per 1,000 posts

Model `gemini-3.1-flash-lite` at **paid-tier** prices of $0.25/M input and $1.5/M output tokens (the free tier was actually used, so the bill was $0).

| Measure | Value |
|---|---|
| LLM calls (incl. failed 503/429, billed $0) | 66 (29 failed) |
| Tokens per post (successful calls) | 281 in / 67 out |
| Cost per 1,000 posts, tagging only | **$0.170** |
| Cost per 1,000 posts, all-in (retries + re-tags after prompt changes) | **$0.180** |
| Infrastructure (Vercel Hobby, Supabase Free, GitHub Actions public, Gemini free tier) | $0 |
