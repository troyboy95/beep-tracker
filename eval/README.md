# Evaluation (task point 3)

Numbers: **[REPORT.md](REPORT.md)** (generated). Raw material: `sample.json` (full context per post) and `labels.csv` (model tags vs gold labels).

## Method

1. `sample_for_review.py` draws 50 posts at random (fixed seed) from **all active tagged posts**, including ones the model rejected as non-fresher, so `is_fresher` is tested in both directions.
2. Each post was checked against its location field and description (`show.py` prints the context) and given gold `role`, `city`, `job_type` and `is_fresher` labels. The labelling rules are the same ones the prompt gives the model:
   - fresher = minimum required experience ≤ 2 years, *or* no years stated, **and** the title is not senior/managerial. Since 2026-11-20 a "Senior"/"Sr." title counts as senior **whatever the years** (strict rule, product decision; this changed post 377's gold label to `False`);
   - city comes from the location field; listed cities are used before "Other (India)".
3. Where the model's label differs but is a reasonable reading (e.g. *Design* vs *Marketing & Content* for a video editor), the field is marked `alt_ok`. The report shows **strict** and **lenient** accuracy.
4. `score.py` computes accuracy with 95% Wilson intervals (n = 50 is small), fresher precision/recall, and cost per 1,000 posts from the `llm_calls` ledger.

**Confirming the labels:** the first labelling pass was done by Claude (an LLM checking an LLM). To make it a true hand-check, review `labels.csv`. Edit any `gold_*`, `alt_ok` or `notes` cell you disagree with, set `reviewer` to your name, and re-run:

```bash
PYTHONPATH=pipeline pipeline/.venv/Scripts/python eval/score.py   # rewrites REPORT.md
```

## Results (first pass)

| | Strict | Lenient |
|---|---|---|
| Role | 90% | 100% |
| City | 92% | 94% |
| Job type | 100% | 100% |
| Fresher (0–2 yrs) | 88% | 88% |
| All four correct | 70% | 82% |

Fresher filter, as users see it: **87% precision** (4 of 31 shown posts shouldn't be), **93% recall**.
Cost: **$0.17 per 1,000 posts** tagging-only, **$0.18 all-in** (retries + re-tags), at paid-tier prices; $0 actually billed.

## Where it goes wrong, and fixes

> **Status (2026-11-20):** fixes 1–3 are implemented but **not yet re-scored**. `REPORT.md` still shows the pre-fix numbers, and `labels.csv` records the model's tags *at sampling time*. To measure the fixes, re-sample model tags for the same 50 ids after the next pipeline run, then re-run `score.py`.

| # | Failure | Evidence | Fix | Expected effect |
|---|---|---|---|---|
| 1 | **"Other (India)" used for listed cities** | 3 of 4 strict city errors. Across *all* 44 "Other (India)" posts, **25** name exactly one listed city (Pune 12, Coimbatore 6, Vadodara 4, Kochi 2, Mysuru 1), mostly SmartRecruiters `city \| ST \| India` locations | ✅ `beep/cities.py`: if `location_raw` names exactly one listed city (aliases collapse, e.g. Gurgaon → Delhi NCR), that city overrides the LLM's. `jobs.city_source` records `rule`/`llm`; the ledger keeps the LLM's raw answer. Re-applied to existing posts on every run. | Preview: **30 of 454** posts corrected. City ~92% → ~98% on this sample |
| 2 | **Managerial titles slip through** | Paytm "Team Leader" ×2 tagged fresher (and the identical Sonipat post *rejected* in another run, which is inconsistent); "AM" (Assistant Manager) tagged fresher | ✅ Senior-title filter adds `leader`, `avp`, and case-sensitive grades `AM`/`AGM`/`DGM`/`GM`/`TL` (not `DM`, which often means Digital Marketing) | Removes 3 of 4 false positives in the sample |
| 3 | **Regex word boundaries vs underscores** | Bosch title `IN_RBIN_Senior Engineer_…` wasn't caught as senior: `_` is a word character, so `\bSenior` never matches | ✅ `_` → space before title matching. With the strict "Senior" rule this also drops Bosch "Senior Engineer"-grade posts asking 2+ yrs (deliberate). Known false positive: `PTC_Workgroup_Manager` (a product name) | Preview for fixes 2+3: **28** active posts dropped at the next full run, **18** of them public (281 → ~263) |
| 4 | **Pre-filter picks the wrong "min years"** | Druva "5–8 yrs … at least 2+ as SE" → hint 2 (min of all numbers); several Bosch posts state "3 to 6 Years" on a separate line from "Experience :" → missed | Prefer the first range in an experience clause; widen the context window / match "Experience :" headers | Fewer `le2`/`no_signal` mislabels, so fewer wasted LLM calls (the LLM corrected the outcome each time) |
| 5 | **Context-word bias on `is_fresher`** | MongoDB *Early Talent Recruiter* (needs 4+ yrs) tagged fresher; the posting is *about* hiring interns | Prompt rule: judge the candidate's required experience, not the audience the role serves; add as a few-shot example | Removes this false-positive class |
| 6 | **Rule-vs-reality borderline** | Posts with no stated years but senior-sounding duties (Workday Analyst "spearhead… architectural solutions") count as fresher *by rule* | Product decision: keep the generous rule (better recall) or require an explicit early-career signal (better precision) | Trade-off. Currently the rule favours showing more posts. |

What works well: **job type is 100%**. The model *rejected* every clearly senior post in the sample (5–9 yr Bosch roles, account executives). Big-city mapping (Bengaluru, Delhi NCR via Gurgaon/Noida, Mumbai, Hyderabad) is reliable.
