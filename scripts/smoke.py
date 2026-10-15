#!/usr/bin/env python3
"""End-to-end smoke test against a running album (compose or cluster).

Usage: python3 scripts/smoke.py [BASE_URL] [API_URL]
  BASE_URL  public entry point (gateway / Ingress), default http://localhost:8088
  API_URL   optional direct api address, used only for /readyz

Uploads a generated PNG, waits for DONE, verifies both thumbnails and the original
download through the public entry point, then deletes the photo.
Standard library only, so it runs anywhere Python 3 exists.
"""

import json
import os
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zlib

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8088").rstrip("/")
API_URL = (sys.argv[2] if len(sys.argv) > 2 else "").rstrip("/")
TIMEOUT_S = 60

# PostSync connects to the private Traefik Service but preserves the signed public Host.
SMOKE_HOST = os.environ.get("SMOKE_HOST", "")


class IngressTransport(urllib.request.BaseHandler):
    handler_order = 400

    def http_request(self, req):
        if SMOKE_HOST:
            target = urllib.parse.urlsplit(req.full_url)
            transport = urllib.parse.urlsplit(BASE)
            if target.netloc in (SMOKE_HOST, transport.netloc):
                req.full_url = urllib.parse.urlunsplit(
                    (transport.scheme, transport.netloc, target.path, target.query, target.fragment)
                )
                req.add_unredirected_header("Host", SMOKE_HOST)
        return req

    https_request = http_request


OPENER = urllib.request.build_opener(IngressTransport())


def png(width: int, height: int) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    row = b"\x00" + bytes([200, 60, 60]) * width
    raw = zlib.compress(row * height)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", raw) + chunk(b"IEND", b"")


def request(method: str, path: str, body: bytes | None = None, headers: dict | None = None):
    url = path if path.startswith("http") else BASE + path
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    with OPENER.open(req, timeout=10) as res:
        return res.status, res.headers, res.read()  # headers lookup is case-insensitive


def webp_size(data: bytes) -> tuple[int, int]:
    assert data[:4] == b"RIFF" and data[8:12] == b"WEBP", "not a WebP file"
    kind = data[12:16]
    if kind == b"VP8 ":
        w, h = struct.unpack("<HH", data[26:30])
        return w & 0x3FFF, h & 0x3FFF
    if kind == b"VP8L":
        b = int.from_bytes(data[21:25], "little")
        return (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
    if kind == b"VP8X":
        return int.from_bytes(data[24:27], "little") + 1, int.from_bytes(data[27:30], "little") + 1
    raise AssertionError(f"unknown WebP chunk {kind!r}")


def step(msg: str) -> None:
    print(f"- {msg}", flush=True)


def main() -> None:
    if API_URL:  # /readyz is not routed by the gateway/Ingress, so it needs the api address
        status, _, body = request("GET", f"{API_URL}/readyz")
        step(f"readyz {status} {json.loads(body)['checks']}")

    name = f"smoke-{uuid.uuid4().hex[:8]}.png"
    boundary = uuid.uuid4().hex
    original_bytes = png(1200, 600)
    form = (
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\n'
            "Content-Type: image/png\r\n\r\n"
        ).encode()
        + original_bytes
        + f"\r\n--{boundary}--\r\n".encode()
    )
    status, headers, body = request(
        "POST", "/api/photos", form, {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    assert status == 202, status
    photo_id = json.loads(body)["id"]
    step(
        f"uploaded {name} -> {photo_id} (served by {headers.get('X-Served-By')}, "
        f"version {headers.get('X-App-Version')})"
    )

    deadline = time.monotonic() + TIMEOUT_S
    while True:
        photo = json.loads(request("GET", f"/api/photos/{photo_id}")[2])
        if photo["status"] in ("DONE", "FAILED") or time.monotonic() > deadline:
            break
        time.sleep(1)
    assert photo["status"] == "DONE", f"status {photo['status']} after {TIMEOUT_S}s"
    step(f"DONE by {photo['processed_by']}")

    for label, key, expected in (
        ("small", "thumb_small_url", (200, 100)),
        ("medium", "thumb_medium_url", (800, 400)),
    ):
        status, headers, data = request("GET", photo[key])
        assert status == 200 and headers.get("Content-Type") == "image/webp", (status, headers)
        assert webp_size(data) == expected, (label, webp_size(data))
        step(f"thumbnail {label} {webp_size(data)[0]}x{webp_size(data)[1]} webp")

    status, headers, data = request("GET", f"/api/photos/{photo_id}/original")
    assert status == 200, status
    assert data == original_bytes, "original bytes changed"
    step(f"original downloaded ({len(data)} bytes, redirect followed)")

    status, _, _ = request("DELETE", f"/api/photos/{photo_id}")
    assert status == 204, status
    try:
        request("GET", f"/api/photos/{photo_id}")
        raise AssertionError("photo still exists after delete")
    except urllib.error.HTTPError as e:
        assert e.code == 404, e.code
    step("deleted")
    print("SMOKE OK")


if __name__ == "__main__":
    main()
