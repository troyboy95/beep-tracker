"""Credential & connectivity check. Run: `python -m beep.doctor` (from /pipeline).

Exits non-zero if any required check fails. Never prints secret values.
"""

import sys

from pydantic import ValidationError

from beep.config import Settings

REQUIRED_TABLES = ("public.jobs", "public.ingest_runs", "public.llm_calls", "public.public_jobs")


def _ok(name: str, detail: str = "") -> None:
    print(f"  [ok]   {name}{' — ' + detail if detail else ''}")


def _fail(name: str, detail: str) -> None:
    print(f"  [FAIL] {name} — {detail}")


def check_env() -> Settings | None:
    try:
        settings = Settings()  # type: ignore[call-arg]
    except ValidationError as e:
        missing = sorted({str(err["loc"][0]).upper() for err in e.errors()})
        _fail("env", f"missing/invalid: {', '.join(missing)} (see .env.example)")
        return None
    _ok("env", "all required variables present")
    return settings


def check_db(s: Settings) -> bool:
    import psycopg

    try:
        with psycopg.connect(s.database_url.get_secret_value(), connect_timeout=10) as conn:
            missing = [
                t
                for t in REQUIRED_TABLES
                if conn.execute("select to_regclass(%s)", (t,)).fetchone()[0] is None
            ]
    except Exception as e:  # noqa: BLE001 — report any connection error
        _fail("database", f"{type(e).__name__}: {str(e).splitlines()[0]}")
        return False
    if missing:
        _fail("database", f"connected, but schema not applied (missing {', '.join(missing)})")
        return False
    _ok("database", "connected, schema present")
    return True


def check_gemini(s: Settings) -> bool:
    from google import genai

    try:
        client = genai.Client(api_key=s.gemini_api_key.get_secret_value())
        model = client.models.get(model=s.gemini_model)
    except Exception as e:  # noqa: BLE001
        _fail("gemini", f"{type(e).__name__}: {str(e).splitlines()[0]}")
        return False
    _ok("gemini", f"model '{model.name}' available")
    return True


def main() -> int:
    print("Beep Tracker doctor")
    s = check_env()
    if s is None:
        return 1
    results = [check_db(s), check_gemini(s)]
    if not s.revalidate_url:
        print("  [skip] revalidate — REVALIDATE_URL not set (expected until web is deployed)")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
