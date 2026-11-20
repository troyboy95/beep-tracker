# Tagging accuracy: 50-post hand check

- Sample: 50 posts drawn at random (seed `20261120`) from **454 active tagged posts** on 2026-11-20. This includes posts the model *rejected* as non-fresher, so `is_fresher` is tested both ways.
- Reviewer: claude (first pass; pending human confirmation). Gold labels follow the same written rules as the prompt (fresher = minimum required experience ≤ 2 yrs, or none stated and not a senior/managerial role).
- *Strict* = exact match. *Lenient* also accepts a different-but-defensible label the reviewer marked `alt_ok`.

## Accuracy per field

| Field | Strict | Lenient |
|---|---|---|
| role | 45/50 = **90%** (95% CI 79%–96%) | 50/50 = **100%** (95% CI 93%–100%) |
| city | 46/50 = **92%** (95% CI 81%–97%) | 47/50 = **94%** (95% CI 84%–98%) |
| job_type | 50/50 = **100%** (95% CI 93%–100%) | 50/50 = **100%** (95% CI 93%–100%) |
| is_fresher | 44/50 = **88%** (95% CI 76%–94%) | 44/50 = **88%** (95% CI 76%–94%) |
| **all 4 fields** | 35/50 = **70%** (95% CI 56%–81%) | 41/50 = **82%** (95% CI 69%–90%) |

## What users see: the fresher filter

- **Precision** (shown posts that really are fresher-eligible): 27/31 = **87%** (95% CI 71%–95%)
- **Recall** (fresher-eligible posts that get shown): 27/29 = **93%** (95% CI 78%–98%)

## Every disagreement

| id | Post | Field | Model | Gold | Defensible? | Note |
|---|---|---|---|---|---|---|
| 37 | MongoDB: Early Talent Recruiter | is_fresher | True | False | no | Needs 4+ yrs recruiting; model swayed by 'early talent / interns / graduates' wording |
| 58 | Pure Storage: Workday Analyst | role | Operations & Supply Chain | DevOps, Cloud & IT | yes | Workday HCM configuration = HR/IT systems; Operations is a stretch but defensible. No years stated → fresher per rule |
| 102 | Glance: Consultant - AI Governance Specialist | role | Consulting & Strategy | Legal & Compliance | yes | AI governance/risk; 'Consultant' title makes Consulting defensible |
| 211 | Paytm: Project Coordinator - CSR - 6 months Contract | is_fresher | False | True | no | 2–4 yrs → minimum 2 → fresher under our 0–2 rule; model said no |
| 221 | Paytm: Team Leader-LRM- Chennai | is_fresher | True | False | no | Team Leader = managerial; pre-filter misses 'Leader' |
| 222 | Paytm: Team Leader-LRM- Deoria | is_fresher | True | False | no | Team Leader = managerial; same template as Sonipat post the model later rejected — inconsistent |
| 233 | AbbVie: Key Account Specialist, FA | city | Remote (India) | Mumbai | yes | Location 'Mumbai | Remote': a Mumbai field territory; Remote (India) defensible. Description empty in API |
| 262 | Continental: Salesforce DevOps Engineer | city | Other (India) | Mysuru | no | Mysuru is in the city list; model used Other (India) |
| 266 | NielsenIQ: Order Management Specialist | city | Other (India) | Pune | no | Pune is in the city list; model used Other (India) |
| 274 | NielsenIQ: Learning Platform & Customer Education Administra | city | Other (India) | Pune | no | Pune is in the city list; model used Other (India). 3–7 yrs → not fresher (correct) |
| 305 | Swiggy: Executive - Video Editor | role | Design | Marketing & Content | yes | Video editor for a food-media brand; Design defensible |
| 357 | Bosch: 2026/02: HW Developer for Electronic Control Unit | role | Core Engineering | Hardware & Embedded | yes | Power-electronics HW for an ECU; Core Engineering (electrical) defensible |
| 423 | Bosch: EDR Function Responsible for BEG Airbag projects | role | Software Engineering | Hardware & Embedded | yes | Airbag ECU software requirements = embedded; Software Engineering defensible |
| 440 | Bosch: Logistics System Analyst & Rollout Engineer | is_fresher | False | True | no | No years stated, not a senior title → fresher by rule; borderline ('proven experience', project mgmt) |
| 1985 | Paytm: Financial Analyst - AM - Lending | is_fresher | True | False | no | 'AM' = Assistant Manager, a managerial grade; borderline (AM is often 2–4 yrs in India) |

## Cost per 1,000 posts

Model `gemini-3.1-flash-lite` at **paid-tier** prices of $0.25/M input and $1.5/M output tokens (the free tier was actually used, so the bill was $0).

| Measure | Value |
|---|---|
| LLM calls (incl. failed 503/429, billed $0) | 66 (29 failed) |
| Tokens per post (successful calls) | 281 in / 67 out |
| Cost per 1,000 posts, tagging only | **$0.170** |
| Cost per 1,000 posts, all-in (retries + re-tags after prompt changes) | **$0.180** |
| Infrastructure (Vercel Hobby, Supabase Free, GitHub Actions public, Gemini free tier) | $0 |
