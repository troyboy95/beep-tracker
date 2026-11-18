"""LLM tagging: role, city, job type, fresher eligibility. One API call = one ledger row.

`call()` never raises: it returns a CallResult with the verbatim response, usage, and either
validated tags or an error. Retry policy and ledger writes live in the orchestrator (run.py).
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import StrEnum

from pydantic import BaseModel, ValidationError

from beep.config import Settings


class Role(StrEnum):
    SOFTWARE = "Software Engineering"
    DATA = "Data & Analytics"
    AI_ML = "AI / ML"
    DEVOPS = "DevOps, Cloud & IT"
    QA = "QA & Testing"
    SECURITY = "Cybersecurity"
    PRODUCT = "Product Management"
    DESIGN = "Design"
    HARDWARE = "Hardware & Embedded"
    CORE_ENG = "Core Engineering"  # mechanical, electrical, civil, manufacturing
    SALES = "Sales & Business Development"
    MARKETING = "Marketing & Content"
    OPERATIONS = "Operations & Supply Chain"
    FINANCE = "Finance & Accounting"
    HR = "HR & Recruiting"
    SUPPORT = "Customer Support & Success"
    CONSULTING = "Consulting & Strategy"
    LEGAL = "Legal & Compliance"
    HEALTHCARE = "Healthcare & Life Sciences"
    OTHER = "Other"


class City(StrEnum):
    BENGALURU = "Bengaluru"
    MUMBAI = "Mumbai"
    DELHI_NCR = "Delhi NCR"
    HYDERABAD = "Hyderabad"
    PUNE = "Pune"
    CHENNAI = "Chennai"
    KOLKATA = "Kolkata"
    AHMEDABAD = "Ahmedabad"
    JAIPUR = "Jaipur"
    KOCHI = "Kochi"
    COIMBATORE = "Coimbatore"
    CHANDIGARH = "Chandigarh"
    INDORE = "Indore"
    THIRUVANANTHAPURAM = "Thiruvananthapuram"
    MYSURU = "Mysuru"
    NAGPUR = "Nagpur"
    VADODARA = "Vadodara"
    BHUBANESWAR = "Bhubaneswar"
    LUCKNOW = "Lucknow"
    GOA = "Goa"
    REMOTE = "Remote (India)"
    MULTIPLE = "Multiple cities"
    OTHER_INDIA = "Other (India)"
    OUTSIDE = "Outside India"


class JobType(StrEnum):
    INTERNSHIP = "internship"
    FULL_TIME = "full_time"
    OTHER = "other"


class Tag(BaseModel):
    id: int
    role: Role
    city: City
    job_type: JobType
    is_fresher: bool
    confidence: float


class BatchTags(BaseModel):
    items: list[Tag]


PROMPT_VERSION = "v2"

SYSTEM_PROMPT = """You classify job posts for an Indian fresher job board.
For EVERY input post return exactly one item with the same `id`.

Fields:
- role: the job function, from the allowed list. Use the closest fit; "Other" only if none fit.
  "Core Engineering" = mechanical/electrical/civil/manufacturing/process. "Hardware & Embedded" =
  chip, firmware, embedded systems. "AI / ML" only when ML/AI is the core of the job.
  "DevOps, Cloud & IT" includes SRE, infrastructure and IT/system administration.
- city: take it from the `location` field, which is authoritative. Use the excerpt only when
  `location` is empty or just "India". Map to the allowed list exactly:
  Bangalore/Bengaluru -> "Bengaluru"; Chennai -> "Chennai"; Delhi, New Delhi, Gurgaon/Gurugram,
  Noida, Faridabad, Ghaziabad -> "Delhi NCR"; Navi Mumbai/Thane -> "Mumbai";
  Secunderabad -> "Hyderabad". Use "Other (India)" ONLY for Indian cities that are not in the
  list. Remote within India -> "Remote (India)". Two or more different Indian cities ->
  "Multiple cities". Not located in India -> "Outside India".
- job_type: "internship" for internships; "full_time" for permanent/full-time roles incl.
  graduate trainee programs; "other" for contract, temporary, part-time or apprenticeship.
- is_fresher: true when the MINIMUM required experience is 2 years or less, or no experience is
  required (students, interns, recent graduates, trainees, junior/entry-level). Examples:
  "0-2 years" -> true; "1-3 years" -> true; "2+ years" -> true; "3+ years" -> false;
  no experience stated and not a senior/managerial role -> true. Senior, lead or managerial
  roles -> false. `min_years_hint` is regex-extracted (may be wrong or null); verify it.
- confidence: 0.0-1.0, your confidence in role AND city AND is_fresher together.
Base every decision only on the given post. Do not invent information."""

PROMPT_HASH = hashlib.sha256(
    (SYSTEM_PROMPT + json.dumps(BatchTags.model_json_schema(), sort_keys=True)).encode()
).hexdigest()


@dataclass
class PostInput:
    id: int
    title: str
    company: str
    location: str
    hints: str
    min_years_hint: int | None
    excerpt: str


@dataclass
class CallResult:
    model: str
    request: dict
    response_raw: str | None = None
    tags: list[Tag] = field(default_factory=list)
    validation_errors: list[dict] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    error: str | None = None
    retryable: bool = False
    retry_after_s: float | None = None  # server-suggested wait (429 RetryInfo)
    quota_exhausted: bool = False  # daily quota hit: stop calling until it resets

    @property
    def parsed_ok(self) -> bool:
        return self.error is None and not self.validation_errors and bool(self.tags)


class Tagger:
    def __init__(self, settings: Settings):
        from google import genai
        from google.genai import types

        self._types = types
        self._s = settings
        self._client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
        self._last_call = 0.0

    def _pace(self) -> None:
        wait = self._last_call + self._s.gemini_min_interval_s - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    def call(self, posts: list[PostInput]) -> CallResult:
        from google.genai import errors

        payload = [p.__dict__ for p in posts]
        user_content = json.dumps({"posts": payload}, ensure_ascii=False)
        res = CallResult(
            model=self._s.gemini_model,
            request={"prompt_version": PROMPT_VERSION, "posts": payload},
        )
        self._pace()
        t0 = time.monotonic()
        try:
            resp = self._client.models.generate_content(
                model=self._s.gemini_model,
                contents=user_content,
                config=self._types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=BatchTags,
                    temperature=0,
                ),
            )
        except errors.APIError as e:
            res.latency_ms = int((time.monotonic() - t0) * 1000)
            res.error = f"APIError {e.code}: {str(e)[:500]}"
            res.retryable = e.code in (429, 500, 502, 503, 504)
            if e.code == 429:
                res.retry_after_s, res.quota_exhausted = parse_rate_limit(e.details)
            return res
        except Exception as e:  # noqa: BLE001 — network etc.; record and move on
            res.latency_ms = int((time.monotonic() - t0) * 1000)
            res.error = f"{type(e).__name__}: {str(e)[:500]}"
            res.retryable = True
            return res

        res.latency_ms = int((time.monotonic() - t0) * 1000)
        usage = resp.usage_metadata
        if usage:
            res.input_tokens = usage.prompt_token_count or 0
            # Thinking tokens are billed as output.
            res.output_tokens = (usage.candidates_token_count or 0) + (
                getattr(usage, "thoughts_token_count", None) or 0
            )
        res.cost_usd = self._s.llm_cost_usd(res.input_tokens, res.output_tokens)
        res.response_raw = resp.text
        _parse_into(res, {p.id for p in posts})
        return res


def parse_rate_limit(details) -> tuple[float | None, bool]:
    """Extract (retryDelay seconds, is_daily_quota) from a Google RPC 429 error body."""
    try:
        items = (details or {}).get("error", {}).get("details", []) or []
    except AttributeError:
        return None, False
    retry_after, daily = None, False
    for d in items:
        kind = d.get("@type", "")
        if kind.endswith("RetryInfo"):
            delay = str(d.get("retryDelay", "")).rstrip("s")
            if delay.replace(".", "", 1).isdigit():
                retry_after = float(delay)
        elif kind.endswith("QuotaFailure"):
            daily = any(
                "PerDay" in (v.get("quotaId") or "") for v in d.get("violations", []) or []
            )
    return retry_after, daily


def _parse_into(res: CallResult, expected_ids: set[int]) -> None:
    try:
        items = json.loads(res.response_raw or "")["items"]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        res.error = f"unparseable response: {e}"
        return
    seen: set[int] = set()
    for i, item in enumerate(items):
        try:
            tag = Tag.model_validate(item)
        except ValidationError as e:
            res.validation_errors.append({"index": i, "errors": e.errors(include_url=False)})
            continue
        if tag.id not in expected_ids or tag.id in seen:
            res.validation_errors.append({"index": i, "errors": f"bad/duplicate id {tag.id}"})
            continue
        tag.confidence = min(1.0, max(0.0, tag.confidence))
        seen.add(tag.id)
        res.tags.append(tag)
    missing = expected_ids - seen
    if missing:
        res.validation_errors.append({"missing_ids": sorted(missing)})
