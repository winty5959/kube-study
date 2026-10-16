import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "changed_components", Path(__file__).parents[1] / "changed-components.py"
)
if spec is None or spec.loader is None:
    raise RuntimeError("component selection module unavailable")
changes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(changes)


@pytest.mark.parametrize(
    "paths,expected",
    [
        (["k3s/apps/api/app/main.py"], ["api"]),
        (["k3s/apps/worker/worker/main.py", "k3s/infra/minio/Dockerfile"], ["worker", "minio"]),
        (["k3s/apps/frontend/public/app.js"], ["frontend"]),
        (["k3s/docs/plan.md", "k3s/k8s/overlays/dev/kustomization.yaml"], []),
        ([".github/workflows/ci.yaml"], list(changes.CONTEXTS)),
        ([".github/workflows/aks-ci.yaml"], []),
        (["k3s/scripts/tests/test_release.py"], list(changes.CONTEXTS)),
        (["k3s/scripts/changed-components.py"], list(changes.CONTEXTS)),
        (["aks/README.md", ".github/workflows/aks-release.yaml"], []),
    ],
)
def test_select(paths, expected):
    assert changes.select(paths) == expected


def test_workflow_dispatch_rebuilds_every_component():
    assert changes.changed("", "a" * 40) == list(changes.CONTEXTS)
    assert changes.changed("0" * 40, "a" * 40) == list(changes.CONTEXTS)


def test_git_diff_uses_repository_root_for_every_working_directory(monkeypatch):
    captured = {}

    def check_output(command, *, cwd, text):
        captured["cwd"] = cwd
        return "k3s/apps/api/app/main.py\n"

    monkeypatch.setattr(changes.subprocess, "check_output", check_output)
    assert changes.changed("base", "head") == ["api"]
    assert captured["cwd"] == changes.REPOSITORY_ROOT


def test_unchanged_image_keeps_its_published_tag():
    manifest = "  - name: ghcr.io/winty5959/album-worker\n    newTag: sha-1234567\n"
    assert "tag=sha-1234567" in changes.coordinates("worker", "a" * 40, False, manifest)
    assert "changed=false" in changes.coordinates("worker", "a" * 40, False, manifest)
    assert "tag=sha-aaaaaaa" in changes.coordinates("worker", "a" * 40, True, manifest)


def test_refuses_unpublished_unchanged_image():
    with pytest.raises(ValueError, match="published CI tag"):
        changes.coordinates("worker", "a" * 40, False, "")


def test_docker_context_is_repository_relative():
    manifest = "  - name: ghcr.io/winty5959/album-api\n    newTag: sha-1234567\n"
    output = changes.coordinates("api", "a" * 40, True, manifest)
    assert "context=k3s/apps/api" in output
