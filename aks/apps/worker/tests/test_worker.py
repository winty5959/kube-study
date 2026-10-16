import io
import urllib.request

import pytest
from PIL import Image

from worker.health import Heartbeat, serve
from worker.thumbs import make_thumbnails


def _image_bytes(fmt: str, size: tuple[int, int], mode: str = "RGB") -> bytes:
    buf = io.BytesIO()
    Image.new(mode, size, "red" if mode != "P" else 1).save(buf, fmt)
    return buf.getvalue()


@pytest.mark.parametrize(
    ("fmt", "mode"), [("JPEG", "RGB"), ("PNG", "RGBA"), ("PNG", "P"), ("WEBP", "RGB")]
)
def test_thumbnails_fit_longest_side_and_are_webp(fmt, mode):
    out = make_thumbnails(_image_bytes(fmt, (1600, 900), mode), {"s": 200, "m": 800}, 80)
    for name, px in (("s", 200), ("m", 800)):
        with Image.open(io.BytesIO(out[name])) as img:
            assert img.format == "WEBP"
            assert max(img.size) == px
            assert img.size[0] / img.size[1] == pytest.approx(16 / 9, rel=0.02)


def test_small_images_are_not_upscaled():
    out = make_thumbnails(_image_bytes("PNG", (100, 50)), {"m": 800}, 80)
    with Image.open(io.BytesIO(out["m"])) as img:
        assert img.size == (100, 50)


def test_corrupt_image_raises():
    with pytest.raises(OSError):  # PIL.UnidentifiedImageError subclasses OSError
        make_thumbnails(b"\x89PNG\r\n\x1a\n" + b"garbage" * 10, {"s": 200}, 80)


def test_healthz_reflects_heartbeat():
    hb = Heartbeat(timeout_s=60)
    server = serve(0, hb)
    url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        assert urllib.request.urlopen(f"{url}/healthz").status == 200
        hb._last -= 120  # simulate a stuck main loop
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(f"{url}/healthz")
        assert e.value.code == 503
        import worker.main  # noqa: F401  registers the album_thumbnail_* metrics

        assert b"album_thumbnail_jobs_total" in urllib.request.urlopen(f"{url}/metrics").read()
    finally:
        server.shutdown()
