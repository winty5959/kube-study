#!/usr/bin/env python3
"""Change one Kustomize image tag without loading or rewriting Secret generators."""

import argparse
import re
from pathlib import Path


def set_tag(text: str, component: str, tag: str) -> str:
    if component not in {"api", "worker", "frontend", "minio"}:
        raise ValueError("unknown album component")
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", tag):
        raise ValueError("invalid image tag")
    name = f"ghcr.io/winty5959/album-{component}"
    pattern = rf"(  - name: {re.escape(name)}\n    newTag: )[^\n]+"
    updated, count = re.subn(pattern, lambda match: match[1] + tag, text)
    if count == 1:
        return updated
    if count > 1 or f"  - name: {name}\n" in text:
        raise ValueError("ambiguous or unsupported image entry")
    match = re.search(r"^images:\n(?:(?:[ \t].*|)\n)*", text, re.MULTILINE)
    if match is None:
        raise ValueError("Kustomization must have an images section")
    return (
        text[: match.end()]
        + f"  - name: {name}\n    newTag: {tag}\n\n"
        + text[match.end() :]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("component")
    parser.add_argument("tag")
    args = parser.parse_args()
    args.manifest.write_text(
        set_tag(args.manifest.read_text(), args.component, args.tag)
    )


if __name__ == "__main__":
    main()
