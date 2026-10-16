import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "image_tags", Path(__file__).parents[1] / "set-image-tag.py"
)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_changes_only_one_component():
    original = (
        "images:\n  - name: ghcr.io/winty5959/album-aks-api\n"
        "    newTag: old\n\nresources:\n  - base\n"
    )
    updated = module.set_tag(original, "api", "sha-abc1234")
    assert updated == original.replace("newTag: old", "newTag: sha-abc1234")


def test_adds_minio_inside_images_not_the_next_section():
    original = (
        "images:\n  - name: ghcr.io/winty5959/album-aks-api\n"
        "    newTag: old\n\nresources:\n  - base\n"
    )
    updated = module.set_tag(original, "minio", "sha-abc1234")
    assert updated.index("album-aks-minio") < updated.index("resources:")
    assert "newTag: old" in updated
    assert module.set_tag(updated, "minio", "sha-abc1234") == updated


@pytest.mark.parametrize("tag", ["bad\ninjected: true", "", "/bad", "a" * 129])
def test_rejects_invalid_tags(tag):
    with pytest.raises(ValueError):
        module.set_tag("images:\n", "api", tag)


def test_rejects_unknown_component():
    with pytest.raises(ValueError):
        module.set_tag("images:\n", "database", "v1")
