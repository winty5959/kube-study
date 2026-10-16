#!/usr/bin/env python3
"""Select rebuilds from Git changes while retaining scans of unchanged artifacts."""

import argparse
import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
CONTEXTS = {
    "api": "k3s/apps/api",
    "worker": "k3s/apps/worker",
    "frontend": "k3s/apps/frontend",
    "minio": "k3s/infra/minio",
}
SHARED_FILES = {
    ".github/workflows/ci.yaml",
    ".github/workflows/release.yaml",
    "k3s/scripts/changed-components.py",
    "k3s/scripts/set-image-tag.py",
    "k3s/scripts/prepare-release.py",
}
SHARED_PREFIXES = ("k3s/scripts/tests/",)


def select(paths: list[str]) -> list[str]:
    if any(path in SHARED_FILES for path in paths) or any(
        path.startswith(SHARED_PREFIXES) for path in paths
    ):
        return list(CONTEXTS)
    return [
        name
        for name, context in CONTEXTS.items()
        if any(path.startswith(context + "/") for path in paths)
    ]


def changed(base: str, head: str) -> list[str]:
    if not base or set(base) == {"0"}:
        return list(CONTEXTS)
    paths = subprocess.check_output(
        ["git", "diff", "--name-only", "--no-renames", base, head],
        cwd=REPOSITORY_ROOT,
        text=True,
    ).splitlines()
    return select(paths)


def coordinates(component: str, head: str, rebuild: bool, manifest: str) -> str:
    if not re.fullmatch(r"[a-f0-9]{40}", head):
        raise ValueError("head must be a full commit SHA")
    if rebuild:
        tag = f"sha-{head[:7]}"
    else:
        matches = re.findall(
            rf"  - name: ghcr.io/winty5959/album-{component}\n    newTag: ([^\n]+)", manifest
        )
        if len(matches) != 1 or not re.fullmatch(r"sha-[a-f0-9]{7}", matches[0]):
            raise ValueError("unchanged component must have one published CI tag")
        tag = matches[0]
    return f"changed={str(rebuild).lower()}\ntag={tag}\ncontext={CONTEXTS[component]}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="")
    parser.add_argument("--head", required=True)
    parser.add_argument("--component", choices=CONTEXTS)
    args = parser.parse_args()
    components = changed(args.base, args.head)
    if args.component:
        manifest = (PROJECT_ROOT / "k8s/overlays/dev/kustomization.yaml").read_text()
        print(coordinates(args.component, args.head, args.component in components, manifest))
    else:
        print(" ".join(components))


if __name__ == "__main__":
    main()
