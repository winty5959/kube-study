"""Apply SQL migrations in app/migrations in filename order.

Run as `python -m app.migrate`. Each file is applied in its own transaction and
recorded in schema_migrations, so re-running is a no-op. A failing file exits
non-zero; this is what lets the K8s Job / ArgoCD PreSync hook block a rollout.
A cluster-wide advisory lock keeps concurrent runs from racing.
"""

import logging
import os
import sys
from pathlib import Path

import psycopg

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
LOCK_ID = 727274  # arbitrary constant shared by all migrate runs

log = logging.getLogger("migrate")


def pending(conn: psycopg.Connection) -> list[Path]:
    applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
    return [p for p in sorted(MIGRATIONS_DIR.glob("*.sql")) if p.stem not in applied]


def run(database_url: str) -> int:
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (LOCK_ID,))
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        todo = pending(conn)
        for path in todo:
            log.info("applying %s", path.name)
            with conn.transaction():
                conn.execute(path.read_text())
                conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.stem,))
        log.info("migrations up to date (%d applied now)", len(todo))
        return len(todo)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        # Only the DB URL is needed, so the migrate Job does not require S3/Redis settings
        run(os.environ["DATABASE_URL"])
    except Exception:
        log.exception("migration failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
