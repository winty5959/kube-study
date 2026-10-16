#!/usr/bin/env python3
"""Verify Grafana dashboard provisioning and real Prometheus samples for every panel."""

import base64
import json
import math
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from typing import Iterator


@contextmanager
def forward(service: str, local_port: int, remote_port: int) -> Iterator[None]:
    """Keep a port-forward local to the caller and always stop the child process."""
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
                process.wait()


def get_json(url: str, auth: str = "") -> dict:
    """Read one API response without logging credentials or returned content."""
    headers = {"Authorization": f"Basic {auth}"} if auth else {}
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Monitoring HTTP check returned {error.code}") from None


def check_query(expr: str, title: str, deadline: float) -> None:
    """Wait for a finite sample, and fail immediately on invalid PromQL."""
    query = urllib.parse.urlencode({"query": expr})
    while True:
        payload = get_json(f"http://127.0.0.1:19090/api/v1/query?{query}")
        if payload.get("status") != "success":
            raise RuntimeError(f"Prometheus query failed for {title}")
        samples = payload.get("data", {}).get("result", [])
        if any(
            math.isfinite(float(sample["value"][1]))
            for sample in samples
            if len(sample.get("value", [])) > 1
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
    user = base64.b64decode(secret["admin-user"]).decode()
    password = base64.b64decode(secret["admin-password"]).decode()
    auth = base64.b64encode(f"{user}:{password}".encode()).decode()

    with (
        forward("monitoring-grafana", 19000, 80),
        forward("monitoring-kube-prometheus-prometheus", 19090, 9090),
    ):
        deadline = time.monotonic() + 120
        total_panels = 0
        for number in range(1, 6):
            dashboard = get_json(
                f"http://127.0.0.1:19000/api/dashboards/uid/album-{number:02}", auth
            )
            panels = dashboard["dashboard"]["panels"]
            if not panels:
                raise RuntimeError(f"Dashboard {number} has no panels")
            for panel in panels:
                targets = panel.get("targets", [])
                if not targets:
                    raise RuntimeError(f"Dashboard {number} panel has no query")
                for target in targets:
                    expr = target["expr"].replace("$namespace", namespace)
                    check_query(expr, panel["title"], deadline)
            total_panels += len(panels)
            print(f"Dashboard {number}: provisioned, {len(panels)} panels have real samples")

        rules = get_json("http://127.0.0.1:19090/api/v1/rules")
        names = {
            rule["name"]
            for group in rules["data"]["groups"]
            for rule in group["rules"]
        }
        expected = {"AlbumQueueBacklog", "AlbumAPIErrorRate", "AlbumCrashLoop"}
        missing = expected - names
        if missing:
            raise RuntimeError(f"Required album alerts are not loaded: {', '.join(sorted(missing))}")
        print("Three required album alerts loaded in Prometheus")
    if total_panels != 20:
        raise RuntimeError(f"Expected 20 panels, found {total_panels}")
    print(f"Observability passed: five dashboards / twenty panels in {namespace}")


if __name__ == "__main__":
    main()
