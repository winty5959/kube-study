"""Real-service cleanup regression scenarios; run inside the API container.

Uses an isolated Postgres schema, Redis queue and S3 buckets. It never changes
the album's existing rows or objects. See docs/experiments/E-08.md for invocation.
"""

import uuid
from contextlib import closing
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
import redis
from psycopg import sql
from psycopg.rows import dict_row

import app
from app.cleanup import recover, sweep
from app.config import Settings
from app.storage import client, ensure_buckets


def main() -> None:
    """Exercise expired, live, exhausted, lost-enqueue and orphan-object paths."""
    suffix = uuid.uuid4().hex
    schema = f"cleanup_{suffix}"
    s = replace(
        Settings(),
        queue_key=f"test:{suffix}",
        bucket_originals=f"test-o-{suffix}",
        bucket_thumbnails=f"test-t-{suffix}",
    )
    with (
        psycopg.connect(s.database_url, autocommit=True, row_factory=dict_row) as conn,
        redis.Redis.from_url(s.redis_url) as queue,
        closing(client(s.s3_endpoint, s.s3_access_key, s.s3_secret_key)) as s3,
    ):
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        ensure_buckets(s3, s.bucket_originals, s.bucket_thumbnails)
        try:
            for migration in sorted((Path(app.__file__).parent / "migrations").glob("*.sql")):
                conn.execute(migration.read_text())
            # Given four different job states, with all timestamps supplied explicitly.
            now = datetime.now(UTC)
            expired, live, exhausted, pending = [uuid.uuid4() for _ in range(4)]
            for photo_id, status, attempts, started in (
                (expired, "PROCESSING", 0, now - timedelta(minutes=20)),
                (live, "PROCESSING", 0, now),
                (exhausted, "PROCESSING", 2, now - timedelta(minutes=20)),
                (pending, "PENDING", 0, None),
            ):
                conn.execute(
                    "INSERT INTO photos (id, filename, content_type, size_bytes, original_key, "
                    "status, retry_count, processed_by, processing_started_at, created_at) "
                    "VALUES (%s, 'test.png', 'image/png', 1, %s, %s, %s, 'gone-pod', %s, %s)",
                    (
                        photo_id,
                        str(photo_id),
                        status,
                        attempts,
                        started,
                        now - timedelta(minutes=20),
                    ),
                )
            # When cleanup runs, it recovers only expired leases and missing enqueues.
            assert recover(conn, queue, s, 600) == 3
            # Then live work is preserved, exhausted work fails and retries are counted once.
            rows = conn.execute("SELECT id, status, retry_count FROM photos").fetchall()
            actual = {row["id"]: (row["status"], row["retry_count"]) for row in rows}
            assert actual == {
                expired: ("PENDING", 1),
                live: ("PROCESSING", 0),
                exhausted: ("FAILED", 3),
                pending: ("PENDING", 0),
            }
            assert set(queue.lrange(s.queue_key, 0, -1)) == {
                str(expired).encode(),
                str(pending).encode(),
            }
            assert recover(conn, queue, s, 600) == 0
            # Given an old unreferenced object and an equally old referenced original.
            s3.put_object(Bucket=s.bucket_originals, Key="orphan", Body=b"orphan")
            s3.put_object(Bucket=s.bucket_originals, Key=str(live), Body=b"original")
            # When the injected clock makes both objects older than the grace period.
            assert sweep(conn, s3, s, 3600, now + timedelta(days=2)) == 1
            # Then the referenced original remains downloadable.
            body = s3.get_object(Bucket=s.bucket_originals, Key=str(live))["Body"].read()
            assert body == b"original"
            print("cleanup scenarios passed (6 real-service outcomes)")
        finally:
            queue.delete(s.queue_key)
            for bucket in (s.bucket_originals, s.bucket_thumbnails):
                for item in s3.list_objects_v2(Bucket=bucket).get("Contents", []):
                    s3.delete_object(Bucket=bucket, Key=item["Key"])
                s3.delete_bucket(Bucket=bucket)
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
