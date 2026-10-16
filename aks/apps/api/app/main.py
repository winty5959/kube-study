import logging
import time
import uuid
from contextlib import asynccontextmanager
from functools import lru_cache
from urllib.parse import quote

import redis
from fastapi import FastAPI, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app import storage
from app.config import Settings
from app.imagetype import ALLOWED, sniff
from app.metrics import REQUEST_DURATION, UPLOADS, QueueLengthCollector

log = logging.getLogger("api")

PHOTO_COLUMNS = (
    "id, filename, content_type, size_bytes, status, processed_by, retry_count, "
    "original_key, thumb_small_key, thumb_medium_key, created_at, processed_at"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = Settings()
    logging.basicConfig(level=s.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    for sdk_logger in ("boto3", "botocore", "urllib3"):
        logging.getLogger(sdk_logger).setLevel(logging.WARNING)
    # open(wait=False): the process starts even if Postgres is down; /readyz reports it instead
    # check=: validate a pooled connection before use, so requests right after a Postgres
    # restart get a fresh connection instead of a 500 from a dead socket (AdminShutdown)
    pool = ConnectionPool(
        s.database_url,
        min_size=1,
        max_size=10,
        open=False,
        kwargs={"row_factory": dict_row},
        check=ConnectionPool.check_connection,
    )
    pool.open(wait=False)
    rds = redis.Redis.from_url(s.redis_url, socket_timeout=3, socket_connect_timeout=3)
    queue_collector = QueueLengthCollector(rds, s.queue_key)
    REGISTRY.register(queue_collector)
    app.state.settings = s
    app.state.pool = pool
    app.state.redis = rds
    app.state.s3 = storage.client(s.s3_endpoint, s.s3_access_key, s.s3_secret_key)
    # Presigned URLs are signed for the host the browser will call, not the in-cluster name.
    # Clients are cached per public endpoint; bounded so arbitrary Host headers cannot grow it.
    app.state.s3_public = lru_cache(maxsize=8)(
        lambda endpoint: storage.client(endpoint, s.s3_access_key, s.s3_secret_key)
    )
    app.state.buckets_ready = False
    log.info("api %s starting on %s", s.app_version, s.pod_name)
    yield
    REGISTRY.unregister(queue_collector)
    pool.close()
    rds.close()


app = FastAPI(title="album-api", description="Photo uploads and thumbnails.", lifespan=lifespan)


@app.middleware("http")
async def observe(request: Request, call_next):
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
    finally:
        route = request.scope.get("route")
        # Use the route template, not the raw path, to keep label cardinality bounded
        label = route.path if route else "unmatched"
        REQUEST_DURATION.labels(request.method, label, str(status)).observe(
            time.perf_counter() - start
        )
    s: Settings = request.app.state.settings
    response.headers["X-Served-By"] = s.pod_name
    response.headers["X-App-Version"] = s.app_version
    return response


def _public_endpoint(request: Request) -> str:
    """Where the browser reaches object storage: the configured value, or else the same
    scheme://host it used to reach the api (Ingress routes /originals and /thumbnails)."""
    s: Settings = request.app.state.settings
    if s.s3_public_endpoint:
        return s.s3_public_endpoint
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    return f"{scheme}://{request.headers.get('host', request.url.netloc)}"


def _presign(request: Request, bucket: str, key: str | None, **params) -> str | None:
    if not key:
        return None
    s: Settings = request.app.state.settings
    return request.app.state.s3_public(_public_endpoint(request)).generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key, **params},
        ExpiresIn=s.presign_ttl_seconds,
    )


def _to_view(request: Request, row: dict, detail: bool = False) -> dict:
    s: Settings = request.app.state.settings
    view = {
        "id": str(row["id"]),
        "filename": row["filename"],
        "content_type": row["content_type"],
        "size_bytes": row["size_bytes"],
        "status": row["status"],
        "processed_by": row["processed_by"],
        "retry_count": row["retry_count"],
        "created_at": row["created_at"].isoformat(),
        "processed_at": row["processed_at"].isoformat() if row["processed_at"] else None,
        "thumb_small_url": _presign(request, s.bucket_thumbnails, row["thumb_small_key"]),
    }
    if detail:
        view["thumb_medium_url"] = _presign(request, s.bucket_thumbnails, row["thumb_medium_key"])
        view["original_url"] = f"/api/photos/{row['id']}/original"
    return view


def _parse_id(photo_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(photo_id)
    except ValueError:
        raise HTTPException(404, "photo not found") from None


def _get_row(request: Request, photo_id: uuid.UUID) -> dict:
    with request.app.state.pool.connection(timeout=5) as conn:
        row = conn.execute(
            f"SELECT {PHOTO_COLUMNS} FROM photos WHERE id = %s", (photo_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(404, "photo not found")
    return row


@app.post("/api/photos", status_code=202)
def upload(request: Request, file: UploadFile = File(...)):
    s: Settings = request.app.state.settings
    data = file.file.read(s.max_upload_bytes + 1)
    if len(data) > s.max_upload_bytes:
        UPLOADS.labels("rejected").inc()
        raise HTTPException(413, f"file exceeds {s.max_upload_bytes} bytes")
    content_type = sniff(data[:16])
    if content_type not in ALLOWED:
        UPLOADS.labels("rejected").inc()
        raise HTTPException(415, "only JPEG, PNG and WebP images are accepted")

    photo_id = uuid.uuid4()
    key = str(photo_id)
    filename = (file.filename or key)[:255]
    s3 = request.app.state.s3
    try:
        _ensure_buckets(request)
        s3.put_object(Bucket=s.bucket_originals, Key=key, Body=data, ContentType=content_type)
        with request.app.state.pool.connection(timeout=5) as conn:
            conn.execute(
                "INSERT INTO photos (id, filename, content_type, size_bytes, original_key)"
                " VALUES (%s, %s, %s, %s, %s)",
                (photo_id, filename, content_type, len(data), key),
            )
        request.app.state.redis.lpush(s.queue_key, key)
    except Exception:
        UPLOADS.labels("error").inc()
        log.exception("upload %s failed; rolling back", key)
        _discard(request, photo_id, [(s.bucket_originals, key)])
        raise HTTPException(503, "storage unavailable, try again") from None

    UPLOADS.labels("accepted").inc()
    log.debug("accepted %s (%s, %d bytes)", key, content_type, len(data))
    return {"id": key, "status": "PENDING"}


def _discard(request: Request, photo_id: uuid.UUID, objects: list[tuple[str, str]]) -> None:
    """Best-effort removal of a photo's objects and row; leftovers are swept by the cleanup job."""
    for bucket, key in objects:
        try:
            request.app.state.s3.delete_object(Bucket=bucket, Key=key)
        except Exception:
            log.warning("could not delete s3://%s/%s", bucket, key)
    try:
        with request.app.state.pool.connection(timeout=5) as conn:
            conn.execute("DELETE FROM photos WHERE id = %s", (photo_id,))
    except Exception:
        log.warning("could not delete row %s", photo_id)


@app.get("/api/photos")
def list_photos(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    with request.app.state.pool.connection(timeout=5) as conn:
        total = conn.execute("SELECT count(*) AS n FROM photos").fetchone()["n"]
        rows = conn.execute(
            f"SELECT {PHOTO_COLUMNS} FROM photos ORDER BY created_at DESC, id LIMIT %s OFFSET %s",
            (size, (page - 1) * size),
        ).fetchall()
    return {
        "items": [_to_view(request, r) for r in rows],
        "page": page,
        "size": size,
        "total": total,
    }


@app.get("/api/photos/{photo_id}")
def get_photo(request: Request, photo_id: str):
    return _to_view(request, _get_row(request, _parse_id(photo_id)), detail=True)


@app.get("/api/photos/{photo_id}/original")
def download_original(request: Request, photo_id: str):
    s: Settings = request.app.state.settings
    row = _get_row(request, _parse_id(photo_id))
    url = _presign(
        request,
        s.bucket_originals,
        row["original_key"],
        ResponseContentDisposition=f"attachment; filename*=UTF-8''{quote(row['filename'])}",
    )
    return RedirectResponse(url, status_code=307)


@app.delete("/api/photos/{photo_id}", status_code=204)
def delete_photo(request: Request, photo_id: str):
    s: Settings = request.app.state.settings
    row = _get_row(request, _parse_id(photo_id))
    objects = [(s.bucket_originals, row["original_key"])]
    objects += [
        (s.bucket_thumbnails, k) for k in (row["thumb_small_key"], row["thumb_medium_key"]) if k
    ]
    _discard(request, row["id"], objects)
    return Response(status_code=204)


def _ensure_buckets(request: Request) -> bool:
    """Create the buckets once per process. Returns True if this call created/checked them.

    Called from /readyz and from upload, so buckets exist even without a readiness probe.
    """
    if request.app.state.buckets_ready:
        return False
    s: Settings = request.app.state.settings
    storage.ensure_buckets(request.app.state.s3, s.bucket_originals, s.bucket_thumbnails)
    request.app.state.buckets_ready = True
    return True


@app.get("/healthz")
def healthz():
    # Liveness: the process is serving requests. Dependencies are deliberately not checked,
    # otherwise a DB outage would restart every api Pod instead of just draining traffic.
    return {"status": "ok"}


@app.get("/readyz")
def readyz(request: Request):
    s: Settings = request.app.state.settings
    checks: dict[str, str] = {}
    try:
        with request.app.state.pool.connection(timeout=2) as conn:
            conn.execute("SELECT 1")
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {type(e).__name__}"
    try:
        request.app.state.redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {type(e).__name__}"
    try:
        if not _ensure_buckets(request):
            request.app.state.s3.head_bucket(Bucket=s.bucket_originals)
        checks["s3"] = "ok"
    except Exception as e:
        checks["s3"] = f"error: {type(e).__name__}"
    ready = all(v == "ok" for v in checks.values())
    return JSONResponse({"ready": ready, "checks": checks}, status_code=200 if ready else 503)


@app.get("/metrics")
def metrics():
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
