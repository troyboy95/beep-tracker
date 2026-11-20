# Evaluation (task point 3)

Numbers: **[REPORT.md](REPORT.md)** (generated). Raw material: `sample.json` (full context per post) and `labels.csv` (model tags vs gold labels).

## Method

1. `sample_for_review.py` draws 50 posts at random (fixed seed) from **all active tagged posts**, including ones the model rejected as non-fresher, so `is_fresher` is tested in both directions.
2. Each post was checked against its location field and description (`show.py` prints the context) and given gold `role`, `city`, `job_type` and `is_fresher` labels. The labelling rules are the same ones the prompt gives the model:
   - fresher = minimum required experience ≤ 2 years, *or* no years stated, **and** the title is not senior/managerial. Since 2026-11-20 a "Senior"/"Sr." title counts as senior **whatever the years** (strict rule, product decision; this changed post 377's gold label to `False`);
   - city comes from the location field; listed cities are used before "Other (India)".
3. Where the model's label differs but is a reasonable reading (e.g. *Design* vs *Marketing & Content* for a video editor), the field is marked `alt_ok`. The report shows **strict** and **lenient** accuracy.
4. `score.py` computes accuracy with 95% Wilson intervals (n = 50 is small), fresher precision/recall, and cost per 1,000 posts from the `llm_calls` ledger.

**Labels are human-confirmed.** Claude did the first labelling pass, with a note on every disagreement. A human then verified all 50 labels on 2026-11-20 and accepted them without changes (`reviewer` column). To revise a label later, edit its `gold_*`, `alt_ok` or `notes` cell and re-run:

```bash
PYTHONPATH=pipeline pipeline/.venv/Scripts/python eval/score.py labels.csv REPORT.md " (before fixes)"
PYTHONPATH="pipeline:eval" pipeline/.venv/Scripts/python eval/rescore_after_fixes.py   # → REPORT_after.md
```

## Results

Same 50 posts, same gold labels, before and after fixes 1–3 ([REPORT.md](REPORT.md) → [REPORT_after.md](REPORT_after.md)):

| Field | Before (strict) | After (strict) | After (lenient) |
|---|---|---|---|
| Role | 90% | 90% | 100% |
| City | 92% | **100%** | 100% |
| Job type | 100% | 100% | 100% |
| Fresher (0–2 yrs) | 86% | **94%** | 94% |
| **All four correct** | 68% | **84%** | **94%** |
| Fresher precision (what users see) | 84% (26/31) | **96%** (26/27) | |
| Fresher recall | 93% (26/28) | 93% (26/28) | |

Cost: **$0.17 per 1,000 posts** tagging-only, **$0.18 all-in** (retries + re-tags), at paid-tier prices; $0 actually billed. The fixes are deterministic, so they add no LLM cost (and the senior-title filter removes some calls).

**Read these "after" numbers with care.** The fixes were designed from errors in *this* sample, so the in-sample gain overstates what a new sample would show. Supporting evidence: the city rule's error class was confirmed across the whole population (25 of 44 "Other (India)" posts, all now fixed). The title rules target patterns (Leader/AM/Senior grades) that recur across Paytm and Bosch boards. A fresh 50-post sample is the honest out-of-sample check.

**What "after" measures:** the system's output once the next *full* run applies everything. City/role/job type are the posts' current DB tags (the city rule is already applied). `is_fresher` is `False` where the new pre-filter drops the post, otherwise the current LLM tag (`rescore_after_fixes.py`).

**Gold-label change:** post 377 (Bosch "Senior Engineer", asks 2+ yrs) was relabelled not-fresher after the strict "Senior" rule was adopted. The "before" column is re-scored with that label, which is why it reads 86% / 84% rather than the first pass's 88% / 87%.

**Errors that remain (8):** 5 role choices that are defensible alternatives (lenient-correct) and 3 `is_fresher` misses:
- MongoDB "Early Talent Recruiter" (needs 4+ yrs) shown: context-word bias, fix #5.
- Paytm CSR coordinator (2–4 yrs) hidden: the LLM is too strict on "minimum 2".
- Bosch logistics analyst (no years stated) hidden: borderline under the generous rule.

## Where it goes wrong, and fixes

> **Status (2026-11-20):** fixes 1–3 are deployed (commit `e20d4a2`; migration 004 and the city rule applied by drain run #10) and re-scored. See Results above.

| # | Failure | Evidence | Fix | Expected effect |
|---|---|---|---|---|
| 1 | **"Other (India)" used for listed cities** | 3 of 4 strict city errors. Across *all* 44 "Other (India)" posts, **25** name exactly one listed city (Pune 12, Coimbatore 6, Vadodara 4, Kochi 2, Mysuru 1), mostly SmartRecruiters `city \| ST \| India` locations | ✅ `beep/cities.py`: if `location_raw` names exactly one listed city (aliases collapse, e.g. Gurgaon → Delhi NCR), that city overrides the LLM's. `jobs.city_source` records `rule`/`llm`; the ledger keeps the LLM's raw answer. Re-applied to existing posts on every run. | Preview: **30 of 454** posts corrected. City ~92% → ~98% on this sample |
| 2 | **Managerial titles slip through** | Paytm "Team Leader" ×2 tagged fresher (and the identical Sonipat post *rejected* in another run, which is inconsistent); "AM" (Assistant Manager) tagged fresher | ✅ Senior-title filter adds `leader`, `avp`, and case-sensitive grades `AM`/`AGM`/`DGM`/`GM`/`TL` (not `DM`, which often means Digital Marketing) | Removes 3 of 4 false positives in the sample |
| 3 | **Regex word boundaries vs underscores** | Bosch title `IN_RBIN_Senior Engineer_…` wasn't caught as senior: `_` is a word character, so `\bSenior` never matches | ✅ `_` → space before title matching. With the strict "Senior" rule this also drops Bosch "Senior Engineer"-grade posts asking 2+ yrs (deliberate). Known false positive: `PTC_Workgroup_Manager` (a product name) | Preview for fixes 2+3: **28** active posts dropped at the next full run, **18** of them public (281 → ~263) |
| 4 | **Pre-filter picks the wrong "min years"** | Druva "5–8 yrs … at least 2+ as SE" → hint 2 (min of all numbers); several Bosch posts state "3 to 6 Years" on a separate line from "Experience :" → missed | Prefer the first range in an experience clause; widen the context window / match "Experience :" headers | Fewer `le2`/`no_signal` mislabels, so fewer wasted LLM calls (the LLM corrected the outcome each time) |
| 5 | **Context-word bias on `is_fresher`** | MongoDB *Early Talent Recruiter* (needs 4+ yrs) tagged fresher; the posting is *about* hiring interns | Prompt rule: judge the candidate's required experience, not the audience the role serves; add as a few-shot example | Removes this false-positive class |
| 6 | **Rule-vs-reality borderline** | Posts with no stated years but senior-sounding duties (Workday Analyst "spearhead… architectural solutions") count as fresher *by rule* | Product decision: keep the generous rule (better recall) or require an explicit early-career signal (better precision) | Trade-off. Currently the rule favours showing more posts. |

What works well: **job type is 100%**. The model *rejected* every clearly senior post in the sample (5–9 yr Bosch roles, account executives). Big-city mapping (Bengaluru, Delhi NCR via Gurgaon/Noida, Mumbai, Hyderabad) is reliable.
