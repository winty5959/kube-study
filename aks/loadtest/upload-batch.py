#!/usr/bin/env python3
"""Upload isolated fixtures, wait for processing, and explicitly clean them up."""

import argparse
import importlib.util
import json
import os
import tempfile
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SMOKE_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "smoke.py"
SMOKE_SPEC = importlib.util.spec_from_file_location("aks_smoke", SMOKE_SCRIPT)
if SMOKE_SPEC is None or SMOKE_SPEC.loader is None:
    raise RuntimeError("Could not load shared PNG fixture helper")
SMOKE_MODULE = importlib.util.module_from_spec(SMOKE_SPEC)
SMOKE_SPEC.loader.exec_module(SMOKE_MODULE)
png = getattr(SMOKE_MODULE, "png")


def save_ids(path: Path, ids: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(ids, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_ids(path: Path) -> list[str]:
    ids = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(ids, list) or not all(isinstance(item, str) for item in ids):
        raise ValueError("ID file must contain a JSON list of photo IDs")
    return ids


def request(
    base: str,
    host_header: str,
    method: str,
    path: str,
    body: bytes | None = None,
    extra_headers: dict[str, str] | None = None,
):
    headers = dict(extra_headers or {})
    if host_header:
        headers["Host"] = host_header
    request = urllib.request.Request(base + path, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read()
        return response.status, json.loads(payload) if payload else None


def status_counts(
    base: str, host_header: str, ids: list[str], concurrency: int
) -> dict[str, int]:
    def status(photo_id: str) -> str:
        _, body = request(base, host_header, "GET", f"/api/photos/{photo_id}")
        return body["status"]

    counts: dict[str, int] = {}
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        for future in as_completed([executor.submit(status, item) for item in ids]):
            result = future.result()
            counts[result] = counts.get(result, 0) + 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=1200)
    parser.add_argument("--base", default="http://album.aks.localhost")
    parser.add_argument("--host-header", default="")
    parser.add_argument(
        "--output", type=Path, default=Path("/tmp/album-batch-ids.json")
    )
    parser.add_argument("--cleanup", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--wait-seconds", type=int, default=0)
    parser.add_argument("--poll-interval", type=int, default=5)
    parser.add_argument("--expect", choices=["DONE", "FAILED"], default="DONE")
    args = parser.parse_args()
    if args.count < 1 or args.concurrency < 1:
        parser.error("count and concurrency must be positive")
    if not (0 < args.width <= 10000 and 0 < args.height <= 10000):
        parser.error("dimensions must be between 1 and 10000 pixels")
    if args.wait_seconds < 0 or args.poll_interval < 1:
        parser.error("wait-seconds cannot be negative and poll-interval must be positive")
    if args.status and args.cleanup:
        parser.error("choose either --status or --cleanup")

    base = args.base.rstrip("/")
    if args.status:
        ids = load_ids(args.output)
        deadline = time.monotonic() + args.wait_seconds
        while True:
            counts = status_counts(base, args.host_header, ids, args.concurrency)
            all_terminal = set(counts).issubset({"DONE", "FAILED"})
            if all_terminal or time.monotonic() >= deadline:
                break
            time.sleep(min(args.poll_interval, max(0, deadline - time.monotonic())))
        print(json.dumps(counts, sort_keys=True))
        if set(counts) != {args.expect}:
            raise RuntimeError("Batch has unexpected photo statuses")
        return

    if args.cleanup:
        ids = load_ids(args.output)

        def delete(photo_id: str) -> None:
            try:
                code, _ = request(base, args.host_header, "DELETE", f"/api/photos/{photo_id}")
            except urllib.error.HTTPError as error:
                if error.code == 404:
                    return
                raise
            if code != 204:
                raise RuntimeError(f"Delete returned HTTP {code}")

        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            list(executor.map(delete, ids))
        print(f"Deleted or already absent: {len(ids)} batch fixtures")
        args.output.unlink()
        return

    if args.output.exists():
        parser.error("output already exists; clean the previous batch first")
    image = png(args.width, args.height)

    def upload(number: int) -> str:
        boundary = f"aksbatch{number:04d}fixture"
        filename = f"batch-{number}.png"
        body = (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            "Content-Type: image/png\r\n\r\n"
        ).encode()
        body += image + f"\r\n--{boundary}--\r\n".encode()
        code, payload = request(
            base,
            args.host_header,
            "POST",
            "/api/photos",
            body,
            {"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        if code != 202:
            raise RuntimeError(f"Upload returned HTTP {code}")
        return payload["id"]

    ids: list[str] = []
    failures = 0
    futures = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [executor.submit(upload, number) for number in range(args.count)]
        for future in as_completed(futures):
            try:
                ids.append(future.result())
            except (OSError, urllib.error.URLError, KeyError, ValueError, RuntimeError):
                failures += 1
            save_ids(args.output, ids)
    if failures:
        raise RuntimeError(f"{failures} uploads failed; accepted IDs saved for cleanup")
    print(
        f"Uploaded {len(ids)} PNG fixtures, {len(image)} bytes each, concurrency {args.concurrency}"
    )


if __name__ == "__main__":
    main()
