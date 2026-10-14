#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run on the dev VM: python3 scripts/check-persistence.py
"""E-08: keep a photo across PostgreSQL, Redis and MinIO Pod replacement."""

import json
import subprocess
import time
import uuid

import smoke


def main() -> None:
    """Create an isolated photo, replace stateful Pods and verify its bytes survive."""
    smoke.BASE = "http://album.dev.local"
    boundary = uuid.uuid4().hex
    original = smoke.png(1200, 600)
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        'filename="persistence.png"\r\nContent-Type: image/png\r\n\r\n'
    ).encode() + original + f"\r\n--{boundary}--\r\n".encode()
    status, _, response = smoke.request(
        "POST", "/api/photos", body,
        {"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    assert status == 202
    photo_id = json.loads(response)["id"]
    try:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            photo = json.loads(smoke.request("GET", f"/api/photos/{photo_id}")[2])
            if photo["status"] == "DONE":
                break
            time.sleep(1)
        assert photo["status"] == "DONE"
        subprocess.run(
            ["kubectl", "-n", "album-dev", "delete", "pod", "postgres-0", "redis-0", "minio-0"],
            check=True,
        )
        for name in ("postgres", "redis", "minio"):
            subprocess.run(
                ["kubectl", "-n", "album-dev", "rollout", "status",
                 f"statefulset/{name}", "--timeout=180s"], check=True,
            )
        subprocess.run(
            ["kubectl", "-n", "album-dev", "wait", "--for=condition=Ready", "pod",
             "-l", "app.kubernetes.io/name=api", "--timeout=120s"], check=True,
        )
        recovered = json.loads(smoke.request("GET", f"/api/photos/{photo_id}")[2])
        assert recovered["status"] == "DONE"
        assert recovered["processed_by"] == photo["processed_by"]
        assert smoke.request("GET", f"/api/photos/{photo_id}/original")[2] == original
        for field, size in (("thumb_small_url", (200, 100)), ("thumb_medium_url", (800, 400))):
            assert smoke.webp_size(smoke.request("GET", recovered[field])[2]) == size
        print("E-08 passed: metadata, original and two thumbnails survived all stateful Pod replacements")
    finally:
        smoke.request("DELETE", f"/api/photos/{photo_id}")


if __name__ == "__main__":
    main()
