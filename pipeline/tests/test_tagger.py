import json

from beep.tagger import CallResult, _parse_into, parse_rate_limit


def test_parse_rate_limit_per_minute():
    body = {"error": {"code": 429, "details": [
        {"@type": "type.googleapis.com/google.rpc.QuotaFailure",
         "violations": [{"quotaId": "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"}]},
        {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "27s"},
    ]}}
    assert parse_rate_limit(body) == (27.0, False)


def test_parse_rate_limit_daily_and_garbage():
    body = {"error": {"details": [{"@type": "x.QuotaFailure", "violations": [
        {"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]}]}}
    assert parse_rate_limit(body) == (None, True)
    assert parse_rate_limit(None) == (None, False)
    assert parse_rate_limit("oops") == (None, False)


def _res(raw: str) -> CallResult:
    r = CallResult(model="m", request={"posts": []}, response_raw=raw)
    return r


def _item(id_, **kw):
    base = {"id": id_, "role": "Software Engineering", "city": "Bengaluru",
            "job_type": "internship", "is_fresher": True, "confidence": 0.9}
    return base | kw


def test_parse_ok():
    r = _res(json.dumps({"items": [_item(1), _item(2, city="Delhi NCR")]}))
    _parse_into(r, {1, 2})
    assert r.parsed_ok and len(r.tags) == 2


def test_parse_missing_and_invalid_items():
    r = _res(json.dumps({"items": [_item(1), _item(2, role="Astronaut"), _item(99)]}))
    _parse_into(r, {1, 2, 3})
    assert [t.id for t in r.tags] == [1]
    assert not r.parsed_ok
    assert {"missing_ids": [2, 3]} in r.validation_errors


def test_parse_garbage():
    r = _res("not json")
    _parse_into(r, {1})
    assert r.error and not r.tags


def test_confidence_clamped():
    r = _res(json.dumps({"items": [_item(1, confidence=1.7)]}))
    _parse_into(r, {1})
    assert r.tags[0].confidence == 1.0
