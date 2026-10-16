import os
import socket
from dataclasses import dataclass, field


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(f"missing required environment variable {name}")
    return value


def _int(name: str, default: int) -> int:
    return int(_env(name, str(default)))


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: _env("DATABASE_URL"))
    redis_url: str = field(default_factory=lambda: _env("REDIS_URL"))
    s3_endpoint: str = field(default_factory=lambda: _env("S3_ENDPOINT"))
    s3_access_key: str = field(default_factory=lambda: _env("S3_ACCESS_KEY"))
    s3_secret_key: str = field(default_factory=lambda: _env("S3_SECRET_KEY"))
    bucket_originals: str = field(default_factory=lambda: _env("BUCKET_ORIGINALS", "originals"))
    bucket_thumbnails: str = field(default_factory=lambda: _env("BUCKET_THUMBNAILS", "thumbnails"))
    queue_key: str = field(default_factory=lambda: _env("QUEUE_KEY", "thumbnail:jobs"))
    thumb_small_px: int = field(default_factory=lambda: _int("THUMB_SMALL_PX", 200))
    thumb_medium_px: int = field(default_factory=lambda: _int("THUMB_MEDIUM_PX", 800))
    webp_quality: int = field(default_factory=lambda: _int("WEBP_QUALITY", 80))
    max_attempts: int = field(default_factory=lambda: _int("MAX_ATTEMPTS", 3))
    # Slows each job down on purpose so KEDA scaling is easy to observe (PRD 4.4)
    artificial_delay_ms: int = field(default_factory=lambda: _int("ARTIFICIAL_DELAY_MS", 0))
    poll_timeout_s: int = field(default_factory=lambda: _int("POLL_TIMEOUT_S", 5))
    # /healthz fails when the main loop has not ticked for this long (stuck worker)
    heartbeat_timeout_s: int = field(default_factory=lambda: _int("HEARTBEAT_TIMEOUT_S", 120))
    metrics_port: int = field(default_factory=lambda: _int("METRICS_PORT", 8001))
    pod_name: str = field(default_factory=lambda: _env("POD_NAME", socket.gethostname()))
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO"))

    @property
    def processing_key(self) -> str:
        # Per-Pod in-flight list. A container restarted after OOMKilled keeps its Pod name,
        # so it can find and requeue the job it was holding when it died.
        return f"{self.queue_key}:processing:{self.pod_name}"
