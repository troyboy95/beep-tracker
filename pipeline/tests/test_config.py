from beep.config import Settings


def _settings(**overrides) -> Settings:
    base = dict(
        database_url="postgresql://u:p@localhost/db",
        gemini_api_key="k",
        gemini_price_input_per_m=0.25,
        gemini_price_output_per_m=1.50,
    )
    return Settings(_env_file=None, **(base | overrides))  # type: ignore[call-arg]


def test_llm_cost_usd():
    s = _settings()
    # 1M input @ $0.25 + 100k output @ $1.50 = 0.25 + 0.15
    assert s.llm_cost_usd(1_000_000, 100_000) == 0.40


def test_empty_env_falls_back_to_default(monkeypatch):
    # GitHub Actions passes unset repo Variables as empty strings.
    monkeypatch.setenv("GEMINI_MODEL", "")
    monkeypatch.setenv("HTTP_USER_AGENT", "")
    s = _settings()
    assert s.gemini_model == Settings.model_fields["gemini_model"].default
    assert s.http_user_agent == Settings.model_fields["http_user_agent"].default


def test_secrets_not_leaked_in_repr():
    assert "p@localhost" not in repr(_settings())
