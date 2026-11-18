import pytest

from beep.normalize import (
    eligibility,
    html_to_text,
    is_india,
    llm_excerpt,
    min_years_required,
    normalize,
    title_may_be_fresher,
)
from beep.sources.base import RawPost


@pytest.mark.parametrize(
    "loc,expected",
    [
        ("Bengaluru, Karnataka", True),
        ("Remote - India", True),
        ("Gurugram | IN", True),
        ("Indianapolis, IN", False),
        ("Indiana, US", False),
        ("Singapore", False),
    ],
)
def test_is_india(loc, expected):
    assert is_india(loc) is expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Requires 3+ years of experience in Java", 3),
        ("1-3 years of relevant experience", 1),
        ("Experience: 0 to 2 yrs", 0),
        ("We have 25 years of history. 2+ years experience in sales.", 2),
        ("Up to 2 years of experience", 0),
        ("Founded 10 years ago, we build things", None),
        ("No numbers here", None),
    ],
)
def test_min_years_required(text, expected):
    assert min_years_required(text) == expected


@pytest.mark.parametrize(
    "title,text,keep,reason",
    [
        ("Software Engineer Intern", "5+ years experience", True, "explicit"),
        ("Senior Software Engineer", "0-2 years", False, "senior_title"),
        ("Data Analyst", "Freshers welcome", True, "explicit"),
        ("Backend Engineer", "1-3 years of experience with Go", True, "le2"),
        ("Backend Engineer", "4+ years of experience with Go", False, "gt2"),
        ("Backend Engineer", "Build APIs.", True, "no_signal"),
        ("Engineer II", "1 year experience", False, "senior_title"),
        ("Legal Entity Controller", "Campus hiring team. 9+ years of experience", False, "gt2"),
        ("Data Analyst", "Freshers or up to 2 years of experience", True, "explicit"),
    ],
)
def test_eligibility(title, text, keep, reason):
    e = eligibility(title, text)
    assert (e.keep, e.reason) == (keep, reason)


def test_title_precheck_keeps_senior_intern_edge():
    assert title_may_be_fresher("Product Management Intern")
    assert not title_may_be_fresher("Staff Engineer")


def test_html_to_text():
    assert html_to_text("&lt;p&gt;Hello&amp;nbsp;<b>world</b>&lt;/p&gt;") == "Hello world"


def test_excerpt_includes_experience_sentence():
    text = "A" * 500 + ". Unrelated sentence. You need 1-2 years of experience in Python."
    assert "1-2 years of experience" in llm_excerpt(text)


def _raw(**kw):
    base = dict(source="greenhouse", board="b", external_id="1", url="https://X.com/j#frag",
                title="SDE Intern", company="Acme", location_raw="Pune, India",
                description="<p>Join us</p>")
    return RawPost(**(base | kw))


def test_normalize_hashes():
    a, b = normalize(_raw()), normalize(_raw(external_id="2"))
    assert a.url == "https://x.com/j"
    assert a.dedup_key == b.dedup_key  # same company/title/location across ids
    assert a.content_hash == b.content_hash
    assert normalize(_raw(description="changed")).content_hash != a.content_hash
