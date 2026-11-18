"""Clean text, India filter, fresher eligibility (0–2 yrs), hashing for change detection + dedup."""

import hashlib
import html
import re
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from beep.sources.base import RawPost

DESCRIPTION_MAX = 6000  # stored
EXCERPT_MAX = 1400  # sent to the LLM

# ------------------------------------------------------------------ text

_TAG = re.compile(r"<[^>]+>")
_BLOCK = re.compile(r"</?(p|div|li|ul|ol|br|h[1-6]|tr)[^>]*>", re.I)
_WS = re.compile(r"[ \t\r\f\v]+")
_NL = re.compile(r"\n\s*\n+")


def html_to_text(raw: str) -> str:
    text = html.unescape(raw or "")
    text = _BLOCK.sub("\n", text)
    text = _TAG.sub(" ", text)
    text = html.unescape(text).replace("\xa0", " ")  # double-escaped sources, nbsp
    text = _WS.sub(" ", text)
    return _NL.sub("\n", text).strip()


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, ""))


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


# ------------------------------------------------------------------ India

INDIA_CITIES = (
    "india|bengaluru|bangalore|mumbai|navi mumbai|thane|delhi|new delhi|gurgaon|gurugram|noida|"
    "greater noida|faridabad|ghaziabad|hyderabad|secunderabad|pune|chennai|kolkata|ahmedabad|"
    "gandhinagar|jaipur|kochi|cochin|coimbatore|chandigarh|mohali|indore|trivandrum|"
    "thiruvananthapuram|mysore|mysuru|nagpur|vadodara|baroda|surat|bhubaneswar|lucknow|goa|"
    "visakhapatnam|vizag|mangalore|mangaluru|hubli|nashik|aurangabad|bhopal|patna|ranchi|"
    "dehradun|kanpur|madurai|tiruchirappalli|vellore|manesar|sriperumbudur|hosur"
)
_INDIA = re.compile(rf"\b({INDIA_CITIES})\b", re.I)


def is_india(location_raw: str) -> bool:
    return bool(_INDIA.search(location_raw or ""))


# ------------------------------------------------------------------ fresher eligibility

SENIOR_TITLE = re.compile(
    r"\b(senior|sr\.?|lead|manager|mgr|director|principal|staff|head|vp|vice president|"
    r"architect|chief|cto|ceo|cfo|partner|expert|specialist ii|ii|iii|iv)\b",
    re.I,
)
# Explicit fresher/early-career signals (title or description).
EXPLICIT = re.compile(
    r"(\bintern(ship)?s?\b|\btrainee\b|\bapprentice(ship)?\b|\bfreshers?\b|\bnew grad|"
    r"\brecent(ly)? graduat|\bgraduate (program|engineer|trainee|analyst)|\bentry[- ]level\b|"
    r"\bcampus\b|\bjunior\b|\bjr\.?\s|no (prior )?experience (is )?required|"
    r"\b(batch|class) of 20(25|26|27)\b|\b20(25|26|27) (batch|graduates?|pass[- ]?outs?)\b|"
    r"\b0\s*(-|–|to)\s*[12]\+?\s*(years?|yrs?))",
    re.I,
)
_YEARS = re.compile(
    r"(\d{1,2})\s*(?:\+|plus)?\s*(?:(?:-|–|to)\s*(\d{1,2})\s*)?(?:\+\s*)?(?:years?|yrs?)",
    re.I,
)
_UPTO = re.compile(r"(?:up ?to|less than|under|<)\s*([12])\s*(?:years?|yrs?)", re.I)
_EXP_CTX = re.compile(r"experience|exp\b|background|working", re.I)

MAX_FRESHER_YEARS = 2


def min_years_required(text: str) -> int | None:
    """Smallest 'N years' figure that appears in an experience context, else None."""
    vals: list[int] = []
    for m in _YEARS.finditer(text):
        window = text[max(0, m.start() - 80) : m.end() + 80]
        if _EXP_CTX.search(window):
            n = int(m.group(1))
            if n <= 30:
                vals.append(n)
    if _UPTO.search(text):
        vals.append(0)
    return min(vals) if vals else None


@dataclass(slots=True)
class Eligibility:
    keep: bool
    reason: str  # explicit | le2 | no_signal | senior_title | gt2
    min_years: int | None


def title_may_be_fresher(title: str) -> bool:
    """Cheap pre-check used by adapters before per-post requests."""
    return bool(EXPLICIT.search(title)) or not SENIOR_TITLE.search(title)


def eligibility(title: str, text: str) -> Eligibility:
    """Deterministic pre-filter. The LLM makes the final `is_fresher` call on kept posts."""
    if EXPLICIT.search(title):
        return Eligibility(True, "explicit", min_years_required(text))
    if SENIOR_TITLE.search(title):
        return Eligibility(False, "senior_title", None)
    my = min_years_required(text)
    # A stated minimum above the cap wins over generic description words ("campus", "interns").
    if my is not None and my > MAX_FRESHER_YEARS:
        return Eligibility(False, "gt2", my)
    if EXPLICIT.search(text):
        return Eligibility(True, "explicit", my)
    if my is None:
        return Eligibility(True, "no_signal", None)
    return Eligibility(True, "le2", my)


# ------------------------------------------------------------------ excerpt for LLM

_KEY_SENT = re.compile(
    r"experience|years|yrs|qualification|graduat|degree|b\.?tech|b\.?e\b|mba|intern|fresher|"
    r"location|based in|office|hybrid|remote|relocat",
    re.I,
)


def llm_excerpt(text: str, limit: int = EXCERPT_MAX) -> str:
    """Opening of the description + sentences about experience/qualifications/location."""
    head = text[:450]
    picked: list[str] = []
    budget = limit - len(head)
    for line in re.split(r"(?<=[.!?])\s+|\n", text[450:]):
        line = line.strip()
        if line and _KEY_SENT.search(line) and len(line) < 400:
            if len(line) + 3 > budget:
                break
            picked.append(line)
            budget -= len(line) + 3
    return head + (" … " + " … ".join(picked) if picked else "")


# ------------------------------------------------------------------ normalized post


@dataclass(slots=True)
class Post:
    source: str
    board: str
    external_id: str
    url: str
    title: str
    company: str
    location_raw: str
    description: str
    posted_at: object
    hints: str
    content_hash: str
    dedup_key: str
    eligibility: Eligibility


def normalize(raw: RawPost) -> Post:
    title = _WS.sub(" ", html.unescape(raw.title)).strip()
    description = html_to_text(raw.description)[:DESCRIPTION_MAX]
    location = _WS.sub(" ", raw.location_raw).strip()
    content_hash = hashlib.sha256(
        "\x1f".join([title, raw.company, location, description, raw.hints]).encode()
    ).hexdigest()
    dedup_key = hashlib.sha256(
        "|".join([_norm(raw.company), _norm(title), _norm(location)]).encode()
    ).hexdigest()[:32]
    return Post(
        source=raw.source,
        board=raw.board,
        external_id=raw.external_id,
        url=canonical_url(raw.url),
        title=title,
        company=raw.company,
        location_raw=location,
        description=description,
        posted_at=raw.posted_at,
        hints=raw.hints,
        content_hash=content_hash,
        dedup_key=dedup_key,
        eligibility=eligibility(title, f"{raw.hints}\n{description}"),
    )
