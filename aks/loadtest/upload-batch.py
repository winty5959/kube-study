#!/usr/bin/env python3
# /// script
# requires-python = "==3.13.*"
# dependencies = ["httpx2[http2,brotli,zstd]"]
# ///
"""Upload isolated fixtures; persist their IDs for polling and explicit cleanup."""

import argparse
import json
import socket
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx2

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from smoke import png


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=1200)
    parser.add_argument("--base", default="http://album.aks.localhost")
    parser.add_argument(
        "--output", type=Path, default=Path("/tmp/album-batch-ids.json")
    )
    parser.add_argument("--cleanup", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--expect", choices=["DONE", "FAILED"], default="DONE")
    args = parser.parse_args()
    if args.count < 1 or args.concurrency < 1:
        parser.error("count and concurrency must be positive")
    if not (0 < args.width <= 10000 and 0 < args.height <= 10000):
        parser.error("dimensions must be between 1 and 10000 pixels")
    transport = httpx2.HTTPTransport(
        http2=True,
        retries=3,
        limits=httpx2.Limits(
            max_connections=200, max_keepalive_connections=40, keepalive_expiry=30
        ),
        socket_options=[(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)],
    )
    with httpx2.Client(
        transport=transport,
        base_url=args.base,
        timeout=httpx2.Timeout(connect=5, read=30, write=10, pool=10),
        follow_redirects=True,
    ) as client:
        if args.status:
            counts: dict[str, int] = {}
            for photo_id in json.loads(args.output.read_text()):
                response = client.get(f"/api/photos/{photo_id}")
                response.raise_for_status()
                status = response.json()["status"]
                counts[status] = counts.get(status, 0) + 1
            print(json.dumps(counts, sort_keys=True))
            if set(counts) != {args.expect}:
                raise RuntimeError("Batch has unexpected photo statuses")
            return
        if args.cleanup:
            ids = json.loads(args.output.read_text())
            for photo_id in ids:
                response = client.delete(f"/api/photos/{photo_id}")
                if response.status_code != 404:
                    response.raise_for_status()
            print(f"Deleted {len(ids)} batch fixtures")
            args.output.unlink()
            return
        if args.output.exists():
            parser.error("output already exists; clean the previous batch first")
        image = png(args.width, args.height)
        ids: list[str] = []

        def upload(number: int) -> str:
            response = client.post(
                "/api/photos",
                files={"file": (f"batch-{number}.png", image, "image/png")},
            )
            response.raise_for_status()
            return response.json()["id"]

        # Save every accepted ID, including when a later request fails.
        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            failures = 0
            for future in as_completed(
                [executor.submit(upload, n) for n in range(args.count)]
            ):
                try:
                    ids.append(future.result())
                except (httpx2.HTTPError, KeyError, ValueError):
                    failures += 1
                args.output.write_text(json.dumps(ids))
            if failures:
                raise RuntimeError(
                    f"{failures} uploads failed; accepted IDs saved for cleanup"
                )
        print(
            f"Uploaded {len(ids)} PNG fixtures, {len(image)} bytes each, concurrency {args.concurrency}"
        )


if __name__ == "__main__":
    main()
