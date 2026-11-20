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


def resolve_city(location_raw: str | None) -> City | None:
    """The single listed city named in `location_raw`, or None if zero or several.

    A "Remote" marker next to one city keeps the city: such posts are tied to that city's
    office or territory (e.g. AbbVie "Mumbai | MH | Remote | India").
    """
    found = {ALIASES[m.group(1).lower()] for m in _PATTERN.finditer(location_raw or "")}
    return found.pop() if len(found) == 1 else None
