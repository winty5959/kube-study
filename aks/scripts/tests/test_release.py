import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "release", Path(__file__).parents[1] / "prepare-release.py"
)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def manifest(tag):
    return "images:\n" + "".join(
        f"  - name: ghcr.io/winty5959/album-aks-{component}\n    newTag: {tag}\n"
        for component in ("api", "worker", "frontend", "minio")
    ) + "\nresources:\n  - base\n"


def test_release_aliases_preserve_recorded_sources():
    dev = manifest("sha-1234abc")
    prod, sources = module.promote(dev, manifest("previous"), "aks-v1.1.0")
    assert prod == manifest("aks-v1.1.0")
    assert set(sources.values()) == {"sha-1234abc"}
    assert len(sources) == 4
    assert dev == manifest("sha-1234abc")


@pytest.mark.parametrize("tag", ["latest", "sha-123", "sha-XYZ1234"])
def test_rejects_unpublished_dev_tags(tag):
    with pytest.raises(ValueError):
        module.promote(manifest(tag), manifest("old"), "aks-v1.1.0")


@pytest.mark.parametrize("tag", ["1.1.0", "v1.1.0", "aks-v1.1", "aks-v01.1.0", "aks-v1.1.0\ninjected"])
def test_rejects_invalid_release_tags(tag):
    with pytest.raises(ValueError):
        module.promote(manifest("sha-1234abc"), manifest("old"), tag)
