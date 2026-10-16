import importlib.util
import json
import urllib.error
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("smoke", Path(__file__).parents[1] / "smoke.py")
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


@pytest.mark.parametrize("changed", [False, True])
def test_original_download_preserves_uploaded_bytes(monkeypatch, changed):
    original = smoke.png(1200, 600)
    deleted = False

    def request(method, path, body=None, headers=None):
        nonlocal deleted
        if method == "POST":
            assert original in body
            return 202, {}, b'{"id": "fixture"}'
        if method == "DELETE":
            deleted = True
            return 204, {}, b""
        if path.endswith("/original"):
            return 200, {}, smoke.png(600, 300) if changed else original
        if path in ("http://fixture/small", "http://fixture/medium"):
            return 200, {"Content-Type": "image/webp"}, path.encode()
        if deleted:
            raise urllib.error.HTTPError(path, 404, "missing", {}, None)
        return (
            200,
            {},
            json.dumps(
                {
                    "status": "DONE",
                    "processed_by": "fixture",
                    "thumb_small_url": "http://fixture/small",
                    "thumb_medium_url": "http://fixture/medium",
                }
            ).encode(),
        )

    monkeypatch.setattr(smoke, "API_URL", "")
    monkeypatch.setattr(smoke, "request", request)
    monkeypatch.setattr(
        smoke, "webp_size", lambda data: (200, 100) if data.endswith(b"small") else (800, 400)
    )
    if changed:
        with pytest.raises(AssertionError, match="original bytes changed"):
            smoke.main()
        assert not deleted
    else:
        smoke.main()
        assert deleted
