"""Deterministic city resolution from the raw location string.

Eval finding (eval/README.md): the LLM tagged 25 of 44 "Other (India)" posts whose location
names exactly one listed city (Pune, Coimbatore, Vadodara, Kochi, Mysuru), mostly
SmartRecruiters "city | ST | India" strings. When the location is unambiguous, a rule is more
accurate and free; the LLM's city is kept only for ambiguous, multi-city or unlisted locations.
"""

import re

from beep.tagger import City

# alias -> canonical City value. Several aliases may map to one city (counted once).
ALIASES: dict[str, City] = {
    "bengaluru": City.BENGALURU, "bangalore": City.BENGALURU,
    "mumbai": City.MUMBAI, "navi mumbai": City.MUMBAI, "thane": City.MUMBAI,
    "delhi": City.DELHI_NCR, "new delhi": City.DELHI_NCR, "gurgaon": City.DELHI_NCR,
    "gurugram": City.DELHI_NCR, "noida": City.DELHI_NCR, "greater noida": City.DELHI_NCR,
    "faridabad": City.DELHI_NCR, "ghaziabad": City.DELHI_NCR, "delhi ncr": City.DELHI_NCR,
    "hyderabad": City.HYDERABAD, "secunderabad": City.HYDERABAD,
    "pune": City.PUNE,
    "chennai": City.CHENNAI,
    "kolkata": City.KOLKATA,
    "ahmedabad": City.AHMEDABAD,
    "jaipur": City.JAIPUR,
    "kochi": City.KOCHI, "cochin": City.KOCHI,
    "coimbatore": City.COIMBATORE,
    "chandigarh": City.CHANDIGARH,
    "indore": City.INDORE,
    "thiruvananthapuram": City.THIRUVANANTHAPURAM, "trivandrum": City.THIRUVANANTHAPURAM,
    "mysuru": City.MYSURU, "mysore": City.MYSURU,
    "nagpur": City.NAGPUR,
    "vadodara": City.VADODARA, "baroda": City.VADODARA,
    "bhubaneswar": City.BHUBANESWAR,
    "lucknow": City.LUCKNOW,
    "goa": City.GOA,
}
_PATTERN = re.compile(
    r"\b(" + "|".join(sorted(map(re.escape, ALIASES), key=len, reverse=True)) + r")\b", re.I
)


# Location segments that are not places of their own: country, work mode, Indian states/UTs
# (names and the two-letter codes ATS boards use).
_NOT_A_PLACE = {
    "india", "ind", "in", "remote", "hybrid", "onsite", "on site", "anywhere",
    # (Delhi, Chandigarh and Goa are deliberately absent: they are also listed cities.)
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh", "gujarat",
    "haryana", "himachal pradesh", "jharkhand", "karnataka", "kerala", "madhya pradesh",
    "maharashtra", "manipur", "meghalaya", "mizoram", "nagaland", "odisha", "punjab",
    "rajasthan", "sikkim", "tamil nadu", "telangana", "tripura", "uttar pradesh", "uttarakhand",
    "uttrakhand", "west bengal", "puducherry", "jammu and kashmir",
    "ladakh", "ncr", "up east", "up west",
    "ap", "ar", "as", "br", "cg", "ga", "gj", "hr", "hp", "jh", "ka", "kl", "mp", "mh", "mn",
    "ml", "mz", "nl", "od", "or", "pb", "rj", "sk", "tn", "ts", "tg", "tr", "up", "uk", "wb",
    "dl", "ch", "py", "jk", "la",
}
_SEGMENT_SPLIT = re.compile(r"[|;/\n]")


def _norm(segment: str) -> str:
    return re.sub(r"[^a-z ]+", " ", segment.lower()).strip()


def resolve_city(location_raw: str | None) -> City | None:
    """The listed city `location_raw` names, or None when it is ambiguous.

    Fires only when EVERY place in the string maps to the same listed city. Segments are split
    on | ; / and newlines; within a segment the first comma part is the place ("Pune, Maharashtra"
    → Pune). Country, state names/codes and work-mode words ("Remote") are ignored, so
    "Mumbai | MH | Remote | India" → Mumbai and "Gurugram | Noida" → Delhi NCR.
    Any place NOT on the list ("Bangalore; Mohali", or 12 towns that include Faridabad) → None:
    the post is multi-city or unlisted, and the LLM decides.
    """
    found: set[City] = set()
    for segment in _SEGMENT_SPLIT.split(location_raw or ""):
        for part in segment.split(",")[:1] or [segment]:
            place = _norm(part)
            if not place or place in _NOT_A_PLACE:
                continue
            hits = {ALIASES[m.group(1).lower()] for m in _PATTERN.finditer(place)}
            if len(hits) != 1:
                return None  # an unlisted place, or two cities in one segment
            found |= hits
    return found.pop() if len(found) == 1 else None
