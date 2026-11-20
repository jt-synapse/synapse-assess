"""Apply numbered SQL migrations and seed the disposable OrderFlow database."""

from pathlib import Path

from orderflow.db import connect

ROOT = Path(__file__).resolve().parents[1]


def main():
    with connect() as db:
        db.execute("SELECT pg_advisory_xact_lock(754001)")
        db.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name text PRIMARY KEY)")
        for migration in sorted((ROOT / "migrations").glob("*.sql")):
            applied = db.execute(
                "SELECT 1 FROM schema_migrations WHERE name = %s", (migration.name,)
            ).fetchone()
            if applied is None:
                db.execute(migration.read_text(encoding="utf-8"))
                db.execute("INSERT INTO schema_migrations VALUES (%s)", (migration.name,))
        db.execute((ROOT / "seed.sql").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
