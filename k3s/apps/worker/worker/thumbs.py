import io

from PIL import Image, ImageOps


def make_thumbnails(data: bytes, sizes: dict[str, int], quality: int) -> dict[str, bytes]:
    """Resize an image so its longest side fits each size; return WebP bytes per size name.

    The full image is decoded on purpose (no JPEG draft mode): memory use then scales with
    pixel count, which is what the OOMKilled experiment (E-06) relies on.
    """
    with Image.open(io.BytesIO(data)) as src:
        img = ImageOps.exif_transpose(src)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
        out = {}
        for name, px in sizes.items():
            thumb = img.copy()
            thumb.thumbnail((px, px), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            thumb.save(buf, "WEBP", quality=quality)
            out[name] = buf.getvalue()
        return out
