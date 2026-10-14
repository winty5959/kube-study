"""Recover expired processing leases and remove old, unreferenced S3 objects.

Run as ``python -m app.cleanup`` in the API image. Redis enqueue happens while
the database row is locked: consumers wait for the transaction to commit.
Duplicate deliveries are harmless because workers only claim PENDING rows.
"""

import logging
import os
from contextlib import closing
from datetime import UTC, datetime, timedelta

import psycopg
import redis
from botocore.client import BaseClient
from psycopg.rows import dict_row

from app.config import Settings
from app.storage import client

log = logging.getLogger("cleanup")


def recover(conn: psycopg.Connection, queue: redis.Redis, s: Settings, stale_s: int) -> int:
    """Recover at most 100 expired jobs per run without taking another cleaner's locks."""
    count = 0
    with conn.transaction():
        rows = conn.execute(
            "SELECT id, status, processed_by, retry_count FROM photos "
            "WHERE (status = 'PROCESSING' AND processing_started_at < "
            "now() - make_interval(secs => %s)) OR "
            "(status = 'PENDING' AND created_at < now() - make_interval(secs => %s)) "
            "ORDER BY created_at LIMIT 100 FOR UPDATE SKIP LOCKED",
            (stale_s, stale_s),
        ).fetchall()
        max_attempts = int(os.environ.get("MAX_ATTEMPTS", "3"))
        for row in rows:
            photo_id = str(row["id"])
            if row["status"] == "PENDING" and queue.lpos(s.queue_key, photo_id) is not None:
                continue
            attempts = row["retry_count"] + int(row["status"] == "PROCESSING")
            failed = attempts >= max_attempts
            conn.execute(
                "UPDATE photos SET status = %s::photo_status, retry_count = %s, "
                "processed_by = NULL, processing_started_at = NULL, "
                "error = 'processing lease expired' WHERE id = %s",
                ("FAILED" if failed else "PENDING", attempts, row["id"]),
            )
            if not failed:
                queue.lpush(s.queue_key, photo_id)
            if row["processed_by"]:
                queue.lrem(f"{s.queue_key}:processing:{row['processed_by']}", 0, photo_id)
            count += 1
    return count


def sweep(
    conn: psycopg.Connection,
    s3: BaseClient,
    s: Settings,
    grace_s: int,
    now: datetime | None = None,
) -> int:
    """Delete only old objects with no live database reference; preserve recent uploads."""
    cutoff = (now or datetime.now(UTC)) - timedelta(seconds=grace_s)
    count = 0
    for bucket in (s.bucket_originals, s.bucket_thumbnails):
        for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket):
            for item in page.get("Contents", []):
                if item["LastModified"] >= cutoff:
                    continue
                key = item["Key"]
                referenced = conn.execute(
                    "SELECT 1 FROM photos WHERE original_key = %s "
                    "OR thumb_small_key = %s OR thumb_medium_key = %s LIMIT 1",
                    (key, key, key),
                ).fetchone()
                if referenced is None:
                    s3.delete_object(Bucket=bucket, Key=key)
                    count += 1
    return count


def main() -> None:
    """Fail the Job on unavailable dependencies so Kubernetes can retry it."""
    s = Settings()
    stale_s = int(os.environ.get("CLEANUP_STALE_SECONDS", "600"))
    grace_s = int(os.environ.get("CLEANUP_OBJECT_GRACE_SECONDS", "86400"))
    if stale_s <= 0 or grace_s <= 0:
        raise RuntimeError("cleanup age thresholds must be positive")
    logging.basicConfig(level=s.log_level)
    with (
        psycopg.connect(s.database_url, row_factory=dict_row, autocommit=True) as conn,
        redis.Redis.from_url(s.redis_url, socket_timeout=5, socket_connect_timeout=3) as queue,
        closing(client(s.s3_endpoint, s.s3_access_key, s.s3_secret_key)) as s3,
    ):
        recovered = recover(conn, queue, s, stale_s)
        removed = sweep(conn, s3, s, grace_s)
    log.info("recovered=%d removed_objects=%d", recovered, removed)


if __name__ == "__main__":
    main()
