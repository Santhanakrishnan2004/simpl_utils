"""PDF / image <-> Base64."""
import base64
import binascii
import re

from ..registry import FileResult, ToolError, tool

G = "Files ↔ Base64"

# (magic prefix, mime type, extension)
_IMAGE_TYPES = [
    (b"\x89PNG\r\n\x1a\n", "image/png", "png"),
    (b"\xff\xd8\xff", "image/jpeg", "jpg"),
    (b"GIF87a", "image/gif", "gif"),
    (b"GIF89a", "image/gif", "gif"),
    (b"BM", "image/bmp", "bmp"),
    (b"\x00\x00\x01\x00", "image/x-icon", "ico"),
]


def detect_image(data: bytes):
    """Return (mime, extension) for known image bytes, else None."""
    for magic, mime, ext in _IMAGE_TYPES:
        if data.startswith(magic):
            return mime, ext
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    head = data[:512].lstrip().lower()
    if head.startswith(b"<svg") or (head.startswith(b"<?xml") and b"<svg" in data[:2048].lower()):
        return "image/svg+xml", "svg"
    return None


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _decode_b64(text: str) -> bytes:
    """Decode plain Base64 or a data: URI (padding optional, whitespace ignored)."""
    s = text.strip()
    m = re.match(r"data:[^,]*;base64,", s, re.I)
    if m:
        s = s[m.end():]
    s = "".join(s.split())
    s = s.replace("-", "+").replace("_", "/")  # accept URL-safe too
    s += "=" * (-len(s) % 4)
    try:
        return base64.b64decode(s, validate=True)
    except (binascii.Error, ValueError) as e:
        raise ToolError(f"invalid Base64: {e}")


@tool("pdf-to-b64", "PDF → Base64", G)
def pdf_to_b64(data: bytes, data_uri: bool = False) -> str:
    """Encode a PDF file as Base64 (optionally as a data: URI)."""
    if not data.lstrip()[:5] == b"%PDF-":
        raise ToolError("this does not look like a PDF file")
    out = _b64(data)
    return f"data:application/pdf;base64,{out}" if data_uri else out


@tool("b64-to-pdf", "Base64 → PDF", G)
def b64_to_pdf(text: str) -> FileResult:
    """Decode Base64 (or a data: URI) back into a PDF file."""
    raw = _decode_b64(text)
    if not raw.lstrip()[:5] == b"%PDF-":
        raise ToolError("decoded data is not a PDF (missing %PDF- header)")
    return FileResult(raw, "output.pdf", "application/pdf")


@tool("image-to-b64", "Image → Base64", G)
def image_to_b64(data: bytes, data_uri: bool = False) -> str:
    """Encode an image (PNG, JPG, GIF, WebP, BMP, ICO, SVG) as Base64 or a data: URI."""
    kind = detect_image(data)
    if kind is None:
        raise ToolError("unrecognised image format (PNG, JPG, GIF, WebP, BMP, ICO, SVG supported)")
    out = _b64(data)
    return f"data:{kind[0]};base64,{out}" if data_uri else out


@tool("b64-to-image", "Base64 → Image", G)
def b64_to_image(text: str) -> FileResult:
    """Decode Base64 (or a data: URI) back into an image file; the format is auto-detected."""
    raw = _decode_b64(text)
    kind = detect_image(raw)
    if kind is None:
        raise ToolError("decoded data is not a recognised image")
    return FileResult(raw, f"output.{kind[1]}", kind[0])
