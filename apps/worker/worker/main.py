"""Thumbnail worker: consume photo ids from Redis and write WebP thumbnails (PRD 4.4).

Reliable queue pattern: BLMOVE moves a job from the shared queue into this Pod's own
processing list, and the job is removed from that list only after the DB is updated.
If the process dies mid-job (e.g. OOMKilled), the restarted container finds the job
there, counts the crash as a failed attempt and requeues it. Jobs left behind by Pods
that are gone for good stay PROCESSING in the DB; the cleanup CronJob (M3) retries them.
"""

import logging
import signal
import time

import boto3
import redis
from botocore.config import Config
from prometheus_client import Counter, Histogram
from psycopg_pool import ConnectionPool

from worker.config import Settings
from worker.health import Heartbeat, serve
from worker.thumbs import make_thumbnails

log = logging.getLogger("worker")

PROCESSING_SECONDS = Histogram(
    "album_thumbnail_processing_seconds",
    "Time to produce both thumbnails for one photo",
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60),
)
JOBS = Counter("album_thumbnail_jobs_total", "Thumbnail jobs by outcome", ["result"])


class Worker:
    def __init__(self, s: Settings):
        self.s = s
        self.stopping = False
        self.heartbeat = Heartbeat(s.heartbeat_timeout_s)
        self.redis = redis.Redis.from_url(
            s.redis_url, socket_connect_timeout=3, socket_timeout=s.poll_timeout_s + 5
        )
        self.pool = ConnectionPool(s.database_url, min_size=1, max_size=2, open=False)
        self.s3 = boto3.client(
            "s3",
            endpoint_url=s.s3_endpoint,
            aws_access_key_id=s.s3_access_key,
            aws_secret_access_key=s.s3_secret_key,
            region_name="us-east-1",
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    # --- queue bookkeeping -------------------------------------------------------------

    def _ack(self, photo_id: str) -> None:
        self.redis.lrem(self.s.processing_key, 1, photo_id)

    def _record_failure(self, photo_id: str, error: str) -> None:
        """Count a failed attempt; requeue it or mark FAILED once attempts are used up."""
        with self.pool.connection(timeout=10) as conn:
            row = conn.execute(
                "UPDATE photos SET retry_count = retry_count + 1,"
                " status = CASE WHEN retry_count + 1 >= %s"
                "   THEN 'FAILED'::photo_status ELSE 'PENDING'::photo_status END,"
                " error = %s"
                " WHERE id = %s AND status IN ('PENDING', 'PROCESSING')"
                " RETURNING status, retry_count",
                (self.s.max_attempts, error[:1000], photo_id),
            ).fetchone()
        pipe = self.redis.pipeline()
        if row and row[0] == "PENDING":
            pipe.lpush(self.s.queue_key, photo_id)
            JOBS.labels("retry").inc()
            log.warning("job %s failed (attempt %d), requeued: %s", photo_id, row[1], error)
        elif row:
            JOBS.labels("failed").inc()
            log.error("job %s FAILED after %d attempts: %s", photo_id, row[1], error)
        pipe.lrem(self.s.processing_key, 1, photo_id)
        pipe.execute()

    def recover_inflight(self) -> None:
        """Requeue jobs this Pod held when its previous container died."""
        orphans = [x.decode() for x in self.redis.lrange(self.s.processing_key, 0, -1)]
        for photo_id in orphans:
            self._record_failure(photo_id, "worker terminated while processing")
        if orphans:
            log.warning("recovered %d in-flight job(s) from a previous crash", len(orphans))

    # --- job ---------------------------------------------------------------------------

    def process(self, photo_id: str) -> None:
        s = self.s
        with self.pool.connection(timeout=10) as conn:
            row = conn.execute(
                "UPDATE photos SET status = 'PROCESSING', processed_by = %s"
                " WHERE id = %s AND status IN ('PENDING', 'PROCESSING')"
                " RETURNING original_key",
                (s.pod_name, photo_id),
            ).fetchone()
        if row is None:  # deleted, or already finished by someone else
            JOBS.labels("skipped").inc()
            self._ack(photo_id)
            return

        started = time.perf_counter()
        try:
            data = self.s3.get_object(Bucket=s.bucket_originals, Key=row[0])["Body"].read()
            if s.artificial_delay_ms:
                time.sleep(s.artificial_delay_ms / 1000)
            thumbs = make_thumbnails(
                data, {"s": s.thumb_small_px, "m": s.thumb_medium_px}, s.webp_quality
            )
            keys = {}
            for size, body in thumbs.items():
                keys[size] = f"{photo_id}_{size}.webp"
                self.s3.put_object(
                    Bucket=s.bucket_thumbnails, Key=keys[size], Body=body, ContentType="image/webp"
                )
            with self.pool.connection(timeout=10) as conn:
                updated = conn.execute(
                    "UPDATE photos SET status = 'DONE', thumb_small_key = %s,"
                    " thumb_medium_key = %s, processed_by = %s, processed_at = now(), error = NULL"
                    " WHERE id = %s",
                    (keys["s"], keys["m"], s.pod_name, photo_id),
                ).rowcount
        except Exception as e:
            log.debug("job %s raised", photo_id, exc_info=True)
            self._record_failure(photo_id, f"{type(e).__name__}: {e}")
            return

        if updated == 0:  # photo deleted while we were working; drop what we wrote
            for key in keys.values():
                self.s3.delete_object(Bucket=s.bucket_thumbnails, Key=key)
            JOBS.labels("skipped").inc()
        else:
            PROCESSING_SECONDS.observe(time.perf_counter() - started)
            JOBS.labels("done").inc()
            log.info("job %s done in %.2fs", photo_id, time.perf_counter() - started)
        self._ack(photo_id)

    # --- loop --------------------------------------------------------------------------

    def run(self) -> None:
        self.pool.open(wait=False)
        recovered = False
        while not self.stopping:
            self.heartbeat.beat()
            try:
                if not recovered:
                    self.recover_inflight()
                    recovered = True
                job = self.redis.blmove(
                    self.s.queue_key, self.s.processing_key, self.s.poll_timeout_s, "RIGHT", "LEFT"
                )
                if job is not None:
                    self.process(job.decode())
            except (redis.ConnectionError, redis.TimeoutError, OSError) as e:
                log.warning("dependency unavailable (%s); retrying in 2s", type(e).__name__)
                time.sleep(2)
            except Exception:
                log.exception("unexpected error in main loop")
                time.sleep(2)
        log.info("stopped")
        self.pool.close()


def main() -> None:
    s = Settings()
    logging.basicConfig(level=s.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    w = Worker(s)

    def stop(signum, _frame):
        # Finish the current job, then exit; BLMOVE returns within poll_timeout_s
        log.info("received signal %d, finishing current job", signum)
        w.stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    serve(s.metrics_port, w.heartbeat)
    log.info("worker %s listening on queue %s", s.pod_name, s.queue_key)
    w.run()


if __name__ == "__main__":
    main()
