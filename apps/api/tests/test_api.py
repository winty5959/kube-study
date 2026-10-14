"""Unit tests that need no running dependencies.

All backing services point at closed local ports, which also exercises the
"dependency down" paths: liveness stays up while readiness fails.
"""

import io

import pytest
from fastapi.testclient import TestClient

from app.imagetype import sniff

PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da63f8ffff3f0005fe02fea7d6a4d30000000049454e44ae426082"
)


@pytest.fixture()
def client(monkeypatch):
    env = {
        "DATABASE_URL": "postgresql://u:p@127.0.0.1:1/db?connect_timeout=1",
        "REDIS_URL": "redis://127.0.0.1:1/0",
        "S3_ENDPOINT": "http://127.0.0.1:1",
        "S3_PUBLIC_ENDPOINT": "http://127.0.0.1:1",
        "S3_ACCESS_KEY": "test",
        "S3_SECRET_KEY": "test",
        "MAX_UPLOAD_BYTES": "1024",
        "APP_VERSION": "test-version",
        "POD_NAME": "test-pod",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.mark.parametrize(
    ("head", "expected"),
    [
        (b"\xff\xd8\xff\xe0rest", "image/jpeg"),
        (PNG_1PX[:16], "image/png"),
        (b"RIFF\x00\x00\x00\x00WEBPVP8 ", "image/webp"),
        (b"GIF89a", None),
        (b"", None),
    ],
)
def test_sniff(head, expected):
    assert sniff(head) == expected


def test_healthz_ok_and_identity_headers(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.headers["X-Served-By"] == "test-pod"
    assert r.headers["X-App-Version"] == "test-version"


def test_readyz_fails_when_dependencies_down(client):
    r = client.get("/readyz")
    assert r.status_code == 503
    body = r.json()
    assert body["ready"] is False
    assert set(body["checks"]) == {"postgres", "redis", "s3"}
    assert all(v != "ok" for v in body["checks"].values())


def test_upload_rejects_non_image(client):
    r = client.post(
        "/api/photos", files={"file": ("a.gif", io.BytesIO(b"GIF89a...."), "image/png")}
    )
    assert r.status_code == 415


def test_upload_rejects_oversize(client):
    big = PNG_1PX + b"\0" * 2048
    r = client.post("/api/photos", files={"file": ("big.png", io.BytesIO(big), "image/png")})
    assert r.status_code == 413


def test_invalid_id_is_404(client):
    assert client.get("/api/photos/not-a-uuid").status_code == 404


def test_metrics_exposed(client):
    client.get("/healthz")
    body = client.get("/metrics").text
    assert "album_http_request_duration_seconds" in body
    assert 'route="/healthz"' in body
