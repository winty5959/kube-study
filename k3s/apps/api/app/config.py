import os
import socket
from dataclasses import dataclass, field


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(f"missing required environment variable {name}")
    return value


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: _env("DATABASE_URL"))
    redis_url: str = field(default_factory=lambda: _env("REDIS_URL"))
    s3_endpoint: str = field(default_factory=lambda: _env("S3_ENDPOINT"))
    # Endpoint the browser uses for presigned URLs (goes through the gateway/Ingress).
    # Empty = derive it from the request Host, so it works behind any tunnel port.
    s3_public_endpoint: str = field(default_factory=lambda: _env("S3_PUBLIC_ENDPOINT", ""))
    s3_access_key: str = field(default_factory=lambda: _env("S3_ACCESS_KEY"))
    s3_secret_key: str = field(default_factory=lambda: _env("S3_SECRET_KEY"))
    bucket_originals: str = field(default_factory=lambda: _env("BUCKET_ORIGINALS", "originals"))
    bucket_thumbnails: str = field(default_factory=lambda: _env("BUCKET_THUMBNAILS", "thumbnails"))
    queue_key: str = field(default_factory=lambda: _env("QUEUE_KEY", "thumbnail:jobs"))
    max_upload_bytes: int = field(
        default_factory=lambda: int(_env("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
    )
    presign_ttl_seconds: int = field(
        default_factory=lambda: int(_env("PRESIGN_TTL_SECONDS", "3600"))
    )
    app_version: str = field(default_factory=lambda: _env("APP_VERSION", "dev"))
    pod_name: str = field(default_factory=lambda: _env("POD_NAME", socket.gethostname()))
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO"))
