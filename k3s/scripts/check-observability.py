#!/usr/bin/env python3
# /// script
# requires-python = "==3.13.*"
# dependencies = ["httpx2[http2,brotli,zstd]"]
# ///
# Run on the matching VM: uv run scripts/check-observability.py dev|prod
"""Verify Grafana dashboard provisioning and real Prometheus samples for every panel."""

import base64
import json
import math
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager

import httpx2


@contextmanager
def forward(service: str, local_port: int, remote_port: int) -> Iterator[None]:
    """Keep a port-forward local to the VM and terminate it even when a check fails."""
    with subprocess.Popen(
        [
            "kubectl",
            "-n",
            "monitoring",
            "port-forward",
            f"service/{service}",
            f"{local_port}:{remote_port}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ) as process:
        try:
            deadline = time.monotonic() + 60
            while True:
                try:
                    with socket.create_connection(("127.0.0.1", local_port), timeout=1):
                        break
                except OSError:
                    if process.poll() is not None or time.monotonic() >= deadline:
                        raise RuntimeError("monitoring port-forward failed") from None
                    time.sleep(0.2)
            yield
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


def observe(response: httpx2.Response) -> None:
    """Record only status on errors, never credentials, headers or response bodies."""
    if response.is_error:
        print(f"Monitoring HTTP check returned {response.status_code}", file=sys.stderr)


def check_query(client: httpx2.Client, expr: str, title: str, deadline: float) -> None:
    """Wait for at least one finite sample, failing on invalid PromQL immediately."""
    while True:
        response = client.get(
            "http://127.0.0.1:19090/api/v1/query", params={"query": expr}
        )
        response.raise_for_status()
        payload = response.json()
        assert payload["status"] == "success"
        if any(
            math.isfinite(float(sample["value"][1]))
            for sample in payload["data"]["result"]
        ):
            return
        if time.monotonic() >= deadline:
            raise RuntimeError(f"No finite sample for {title}")
        time.sleep(2)


def main() -> None:
    """Require five provisioned dashboards and finite values in all twenty panels."""
    environment = sys.argv[1] if len(sys.argv) > 1 else "dev"
    if environment not in ("dev", "prod"):
        raise RuntimeError("environment must be dev or prod")
    namespace = f"album-{environment}"
    secret = json.loads(
        subprocess.check_output(
            [
                "kubectl",
                "-n",
                "monitoring",
                "get",
                "secret",
                "grafana-admin",
                "-o",
                "json",
            ]
        )
    )["data"]
    auth = httpx2.BasicAuth(
        base64.b64decode(secret["admin-user"]).decode(),
        base64.b64decode(secret["admin-password"]).decode(),
    )
    transport = httpx2.HTTPTransport(
        http2=True,
        retries=3,
        limits=httpx2.Limits(
            max_connections=200, max_keepalive_connections=40, keepalive_expiry=30
        ),
        socket_options=[(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)],
    )
    with (
        forward("monitoring-grafana", 19000, 80),
        forward("monitoring-kube-prometheus-prometheus", 19090, 9090),
        httpx2.Client(
            transport=transport,
            timeout=httpx2.Timeout(connect=5, read=30, write=10, pool=10),
            follow_redirects=True,
            event_hooks={"response": [observe]},
        ) as client,
    ):
        deadline = time.monotonic() + 120
        for number in range(1, 6):
            dashboard = client.get(
                f"http://127.0.0.1:19000/api/dashboards/uid/album-{number:02}",
                auth=auth,
            )
            dashboard.raise_for_status()
            panels = dashboard.json()["dashboard"]["panels"]
            assert panels
            for panel in panels:
                for target in panel["targets"]:
                    expr = target["expr"].replace("$namespace", namespace)
                    check_query(client, expr, panel["title"], deadline)
            print(
                f"Dashboard {number}: provisioned, {len(panels)} panels have real samples"
            )
        response = client.get("http://127.0.0.1:19090/api/v1/rules")
        response.raise_for_status()
        names = {
            rule["name"]
            for group in response.json()["data"]["groups"]
            for rule in group["rules"]
        }
        assert {"AlbumQueueBacklog", "AlbumAPIErrorRate", "AlbumCrashLoop"} <= names
        print("Three required album alerts loaded in Prometheus")
    print(f"Observability passed: five dashboards / twenty panels in {namespace}")


if __name__ == "__main__":
    main()
