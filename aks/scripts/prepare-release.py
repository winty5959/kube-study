#!/usr/bin/env python3
"""Prepare release aliases for the exact recorded, CI-published dev artifacts."""

import argparse
import importlib.util
import json
import re
from pathlib import Path


def promote(dev: str, prod: str, release: str) -> tuple[str, dict[str, str]]:
    if not re.fullmatch(r"aks-v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", release):
        raise ValueError("release must use aks-vMAJOR.MINOR.PATCH")
    spec = importlib.util.spec_from_file_location(
        "image_tags", Path(__file__).parent / "set-image-tag.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("image tag helper unavailable")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    sources: dict[str, str] = {}
    for component in ("api", "worker", "frontend", "minio"):
        matches = re.findall(
            rf"  - name: ghcr.io/winty5959/album-aks-{component}\n    newTag: ([^\n]+)", dev
        )
        if len(matches) != 1 or not re.fullmatch(r"sha-[a-f0-9]{7}", matches[0]):
            raise ValueError(f"{component} must have one CI-published sha tag")
        sources[component] = matches[0]
        prod = helper.set_tag(prod, component, release)
    return prod, sources


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", required=True)
    parser.add_argument("--manifest-json", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    dev = (root / "k8s/overlays/dev/kustomization.yaml").read_text()
    prod_path = root / "k8s/overlays/prod/kustomization.yaml"
    prod, sources = promote(dev, prod_path.read_text(), args.release)
    if args.manifest_json:
        args.manifest_json.write_text(json.dumps(sources, indent=2) + "\n")
    if not args.dry_run:
        prod_path.write_text(prod)
    print("\n| Component | Source dev tag | Release alias |\n|---|---|---|")
    for component, source in sources.items():
        print(f"| {component} | {source} | {args.release} |")


if __name__ == "__main__":
    main()
