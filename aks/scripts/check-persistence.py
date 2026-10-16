#!/usr/bin/env python3
# /// script
# requires-python = "==3.13.*"
# dependencies = []
# ///
# Run on dev: uv run --python 3.13 scripts/check-persistence.py
"""E-08: keep a photo across PostgreSQL, Redis and MinIO Pod replacement."""

import json
import subprocess
import time
import urllib.error
import uuid
from http.client import HTTPMessage
from pathlib import Path

import smoke


def available(method: str, path: str) -> tuple[int, HTTPMessage, bytes]:
    """Wait for dependencies and Ingress to converge after their deliberate restart."""
    deadline = time.monotonic() + 60
    transient = 0
    while True:
        try:
            result = smoke.request(method, path)
            if transient:
                print(f"Observed {transient} transient API failures before recovery")
            return result
        except urllib.error.HTTPError as error:
            if method == "DELETE" and error.code == 404:
                return 404, error.headers, b""
            if error.code not in (500, 502, 503, 504) or time.monotonic() >= deadline:
                raise
        except (urllib.error.URLError, OSError):
            if time.monotonic() >= deadline:
                raise
        transient += 1
        time.sleep(1)


def main() -> None:
    """Create an isolated photo, replace stateful Pods and verify its bytes survive."""
    smoke.BASE = "http://album.aks.localhost"
    fixture_file = Path("/tmp/album-e08-id.json")
    if fixture_file.exists():
        raise RuntimeError("Clean the saved E08 fixture before starting another run")
    boundary = uuid.uuid4().hex
    original = smoke.png(1200, 600)
    body = (
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
            'filename="persistence.png"\r\nContent-Type: image/png\r\n\r\n'
        ).encode()
        + original
        + f"\r\n--{boundary}--\r\n".encode()
    )
    status, _, response = smoke.request(
        "POST",
        "/api/photos",
        body,
        {"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    assert status == 202
    photo_id = json.loads(response)["id"]
    fixture_file.write_text(json.dumps([photo_id]))
    try:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            photo = json.loads(smoke.request("GET", f"/api/photos/{photo_id}")[2])
            if photo["status"] == "DONE":
                break
            time.sleep(1)
        assert photo["status"] == "DONE"
        subprocess.run(
            [
                "kubectl",
                "-n",
                "album-dev",
                "delete",
                "pod",
                "postgres-0",
                "redis-0",
                "minio-0",
            ],
            check=True,
        )
        for name in ("postgres", "redis", "minio"):
            subprocess.run(
                [
                    "kubectl",
                    "-n",
                    "album-dev",
                    "rollout",
                    "status",
                    f"statefulset/{name}",
                    "--timeout=180s",
                ],
                check=True,
            )
        subprocess.run(
            [
                "kubectl",
                "-n",
                "album-dev",
                "wait",
                "--for=condition=Ready",
                "pod",
                "-l",
                "app.kubernetes.io/name=api",
                "--timeout=120s",
            ],
            check=True,
        )
        recovered = json.loads(available("GET", f"/api/photos/{photo_id}")[2])
        assert recovered["status"] == "DONE"
        assert recovered["processed_by"] == photo["processed_by"]
        assert available("GET", f"/api/photos/{photo_id}/original")[2] == original
        for field, size in (
            ("thumb_small_url", (200, 100)),
            ("thumb_medium_url", (800, 400)),
        ):
            assert smoke.webp_size(available("GET", recovered[field])[2]) == size
        print(
            "E-08 passed: metadata, original and two thumbnails survived "
            "all stateful Pod replacements"
        )
    finally:
        available("DELETE", f"/api/photos/{photo_id}")
        fixture_file.unlink()


if __name__ == "__main__":
    main()
