#!/usr/bin/env python3
# /// script
# requires-python = "==3.13.*"
# dependencies = ["httpx2[http2,brotli,zstd]"]
# ///
"""Record availability and served versions during a controlled Pod change."""

import argparse
import socket
import time
from datetime import UTC, datetime

import httpx2


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://album.dev.local")
    parser.add_argument("--duration", type=float, default=90)
    parser.add_argument("--interval", type=float, default=0.25)
    args = parser.parse_args()
    if args.duration <= 0 or args.interval <= 0:
        parser.error("duration and interval must be positive")
    transport = httpx2.HTTPTransport(
        http2=True,
        retries=3,
        limits=httpx2.Limits(
            max_connections=200, max_keepalive_connections=40, keepalive_expiry=30
        ),
        socket_options=[(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)],
    )
    failures = 0
    requests = 0
    with httpx2.Client(
        transport=transport,
        timeout=httpx2.Timeout(connect=5, read=30, write=10, pool=10),
        follow_redirects=True,
    ) as client:
        deadline = time.monotonic() + args.duration
        print("time_utc,status,version,pod,latency_ms", flush=True)
        while time.monotonic() < deadline:
            started = time.monotonic()
            status, version, pod = 0, "-", "-"
            try:
                response = client.get(args.base + "/api/photos", params={"size": 1})
                status = response.status_code
                version = response.headers.get("X-App-Version", "-")
                pod = response.headers.get("X-Served-By", "-")
            except httpx2.HTTPError:
                pass
            failures += int(status != 200)
            requests += 1
            print(
                f"{datetime.now(UTC).isoformat()},{status},{version},{pod},"
                f"{(time.monotonic() - started) * 1000:.1f}",
                flush=True,
            )
            time.sleep(args.interval)
    print(f"Requests={requests} failures={failures}", flush=True)
    if failures:
        raise RuntimeError("Availability observation recorded failed requests")


if __name__ == "__main__":
    main()
