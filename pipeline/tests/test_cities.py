import pytest

from beep.cities import resolve_city
from beep.tag_queue import _apply_city_rule
from beep.tagger import City, PostInput, Tag


@pytest.mark.parametrize(
    "loc,expected",
    [
        # SmartRecruiters / Lever formats the LLM mislabelled as "Other (India)" (eval finding)
        ("Pune | MH | India", City.PUNE),
        ("coimbatore | India", City.COIMBATORE),
        ("Mysuru | KA | India", City.MYSURU),
        ("Kochi, KL, India | //KL | India", City.KOCHI),
        ("Vadodara | GJ | India", City.VADODARA),
        # aliases collapse to one canonical city
        ("Gurgaon", City.DELHI_NCR),
        ("New Delhi, Delhi", City.DELHI_NCR),
        ("Bangalore, India", City.BENGALURU),
        ("Hybrid in Bengaluru, India", City.BENGALURU),
        ("Mysore", City.MYSURU),
        # city + remote marker keeps the city (territory/office-bound)
        ("Mumbai | MH | Remote | India", City.MUMBAI),
        # ambiguous / unlisted / none -> leave it to the LLM
        ("Bengaluru | Pune | India", None),
        ("Aligarh, Uttar Pradesh | India", None),
        ("Remote - India", None),
        ("India", None),
        ("", None),
        (None, None),
    ],
)
def test_resolve_city(loc, expected):
    assert resolve_city(loc) == expected


def test_rule_overrides_llm_city_only_when_unambiguous():
    batch = [
        PostInput(1, "t", "c", "Pune | MH | India", "", None, ""),
        PostInput(2, "t", "c", "Aligarh, Uttar Pradesh | India", "", None, ""),
    ]
    tags = [
        Tag(id=1, role="Other", city="Other (India)", job_type="full_time", is_fresher=True,
            confidence=0.9),
        Tag(id=2, role="Other", city="Other (India)", job_type="full_time", is_fresher=True,
            confidence=0.9),
    ]
    sources = _apply_city_rule(tags, batch)
    assert (tags[0].city, sources[1]) == (City.PUNE, "rule")
    assert (tags[1].city, sources[2]) == (City.OTHER_INDIA, "llm")
