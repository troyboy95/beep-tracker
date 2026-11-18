"""Apply db/migrations/*.sql in order, tracked in `schema_migrations`.

Run: python -m beep.migrate
"""

import sys

import psycopg

from beep.config import REPO_ROOT, get_settings

MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations"


def main() -> int:
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    with psycopg.connect(get_settings().database_url.get_secret_value(), autocommit=True) as conn:
        conn.execute(
            "create table if not exists public.schema_migrations ("
            " version text primary key, applied_at timestamptz not null default now())"
        )
        conn.execute("alter table public.schema_migrations enable row level security")
        conn.execute("revoke all on public.schema_migrations from anon, authenticated")
        applied = {r[0] for r in conn.execute("select version from public.schema_migrations")}

        # Baseline: 001 was applied by hand in the SQL editor before this tool existed.
        if not applied and conn.execute("select to_regclass('public.jobs')").fetchone()[0]:
            conn.execute("insert into public.schema_migrations (version) values ('001_init')")
            applied.add("001_init")
            print("baseline: marked 001_init as applied")

        for f in files:
            version = f.stem
            if version in applied:
                continue
            print(f"applying {version} ...")
            with conn.transaction():
                conn.execute(f.read_text(encoding="utf-8"))
                conn.execute(
                    "insert into public.schema_migrations (version) values (%s)", (version,)
                )
        print("migrations up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
