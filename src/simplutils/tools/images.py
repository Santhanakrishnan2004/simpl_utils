"""Image tools (need Pillow: pip install simplutils[files])."""
import io
from typing import List, Literal

from ..registry import FileResult, ToolError, tool

G = "Images"
MAX_SIDE = 20000

# key -> (Pillow format, mime, extension)
_FORMATS = {
    "png": ("PNG", "image/png", "png"),
    "jpg": ("JPEG", "image/jpeg", "jpg"),
    "webp": ("WEBP", "image/webp", "webp"),
    "bmp": ("BMP", "image/bmp", "bmp"),
    "gif": ("GIF", "image/gif", "gif"),
}
_BY_PIL = {v[0]: k for k, v in _FORMATS.items()}


def _pil():
    try:
        from PIL import Image, ImageOps
    except ImportError:
        raise ToolError("this tool needs Pillow: pip install simplutils[files]")
    return Image, ImageOps


def _open(data: bytes):
    """Open an image, honour EXIF rotation. Returns (image, source format key)."""
    Image, ImageOps = _pil()
    try:
        img = Image.open(io.BytesIO(data))
        fmt = _BY_PIL.get(img.format, "png")
        img.load()
        return ImageOps.exif_transpose(img), fmt
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"cannot read image: {e}")


def _flatten(img):
    """Convert to RGB, putting transparency on a white background."""
    Image, _ = _pil()
    if img.mode in ("RGB", "L"):
        return img
    rgba = img.convert("RGBA")
    bg = Image.new("RGB", rgba.size, (255, 255, 255))
    bg.paste(rgba, mask=rgba.split()[3])
    return bg


def _check_quality(q: int) -> None:
    if not 1 <= q <= 100:
        raise ToolError("quality must be 1-100")


def _encode(img, key: str, quality: int = 90) -> bytes:
    pil_fmt = _FORMATS[key][0]
    params = {}
    if pil_fmt == "JPEG":
        img = _flatten(img)
        params = {"quality": quality, "optimize": True}
    elif pil_fmt == "WEBP":
        params = {"quality": quality}
    elif pil_fmt == "PNG":
        params = {"optimize": True}
    buf = io.BytesIO()
    try:
        img.save(buf, pil_fmt, **params)
    except Exception as e:
        raise ToolError(f"cannot save as {key}: {e}")
    return buf.getvalue()


def _result(data: bytes, key: str, stem: str) -> FileResult:
    _, mime, ext = _FORMATS[key]
    return FileResult(data, f"{stem}.{ext}", mime)


@tool("image-convert", "Image Convert", G)
def image_convert(data: bytes, to: Literal["png", "jpg", "webp", "bmp", "gif"] = "png", quality: int = 90) -> FileResult:
    """Convert an image to PNG, JPG, WebP, BMP or GIF (animated images keep only the first frame)."""
    _check_quality(quality)
    img, _ = _open(data)
    return _result(_encode(img, to, quality), to, "converted")


@tool("image-resize", "Image Resize", G)
def image_resize(data: bytes, width: int = 0, height: int = 0, scale: int = 0, exact: bool = False) -> FileResult:
    """Resize by width, height, or percent `scale`. Width+height fits inside the box (aspect kept) unless `exact`."""
    Image, _ = _pil()
    if min(width, height, scale) < 0:
        raise ToolError("values cannot be negative")
    if not (width or height or scale):
        raise ToolError("give a width, a height, or a scale (percent), e.g. --width 800")
    if scale and (width or height):
        raise ToolError("use either scale or width/height, not both")
    img, key = _open(data)
    w0, h0 = img.size
    if scale:
        w, h = round(w0 * scale / 100), round(h0 * scale / 100)
    elif width and height:
        if exact:
            w, h = width, height
        else:
            ratio = min(width / w0, height / h0)
            w, h = round(w0 * ratio), round(h0 * ratio)
    elif width:
        w, h = width, round(h0 * width / w0)
    else:
        w, h = round(w0 * height / h0), height
    w, h = max(w, 1), max(h, 1)
    if max(w, h) > MAX_SIDE:
        raise ToolError(f"result would be {w}x{h}; the limit is {MAX_SIDE}px per side")
    resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
    return _result(_encode(img.resize((w, h), resample), key), key, "resized")


@tool("image-compress", "Image Compress", G)
def image_compress(data: bytes, quality: int = 70, max_width: int = 0) -> FileResult:
    """Shrink file size (JPG/WebP use `quality`; PNG is optimised losslessly). Optionally cap the width."""
    Image, _ = _pil()
    _check_quality(quality)
    img, key = _open(data)
    resized = False
    if max_width and img.width > max_width:
        h = max(round(img.height * max_width / img.width), 1)
        img = img.resize((max_width, h), getattr(getattr(Image, "Resampling", Image), "LANCZOS"))
        resized = True
    out = _encode(img, key, quality)
    if len(out) >= len(data) and not resized:
        out = data  # could not improve; keep the original bytes
    return _result(out, key, "compressed")


@tool("image-info", "Image Info", G)
def image_info(data: bytes) -> str:
    """Show an image's format, dimensions, colour mode and file size."""
    Image, _ = _pil()
    try:
        img = Image.open(io.BytesIO(data))
        fmt, size, mode = img.format, img.size, img.mode
        frames = getattr(img, "n_frames", 1)
    except Exception as e:
        raise ToolError(f"cannot read image: {e}")
    lines = [f"format: {fmt}", f"size: {size[0]} x {size[1]} px", f"mode: {mode}", f"file size: {len(data):,} bytes"]
    if frames > 1:
        lines.append(f"frames: {frames}")
    return "\n".join(lines)


@tool("image-to-pdf", "Images → PDF", G)
def image_to_pdf(files: List[bytes]) -> FileResult:
    """Combine one or more images into a single PDF (one image per page, in the order given)."""
    pages = [_flatten(_open(f)[0]) for f in files]
    buf = io.BytesIO()
    try:
        pages[0].save(buf, "PDF", save_all=True, append_images=pages[1:], resolution=100.0)
    except Exception as e:
        raise ToolError(f"cannot build PDF: {e}")
    return FileResult(buf.getvalue(), "images.pdf", "application/pdf")
