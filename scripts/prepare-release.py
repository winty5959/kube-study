#!/usr/bin/env python3
"""Promote the exact recorded dev tags, preserving build-once release artifacts."""

import importlib.util
import re
from pathlib import Path


def main() -> None:
    directory = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("image_tags", directory / "set-image-tag.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("image tag helper unavailable")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    root = directory.parent
    dev = (root / "k8s/overlays/dev/kustomization.yaml").read_text()
    prod_path = root / "k8s/overlays/prod/kustomization.yaml"
    prod = prod_path.read_text()
    print("\n| Component | Existing dev tag |\n|---|---|")
    for component in ("api", "worker", "frontend", "minio"):
        matches = re.findall(
            rf"  - name: ghcr.io/winty5959/album-{component}\n    newTag: ([^\n]+)", dev
        )
        if len(matches) != 1 or not re.fullmatch(r"sha-[a-f0-9]{7}", matches[0]):
            raise RuntimeError(f"{component} must have one CI-published sha tag")
        prod = helper.set_tag(prod, component, matches[0])
        print(f"| {component} | {matches[0]} |")
    prod_path.write_text(prod)


if __name__ == "__main__":
    main()
