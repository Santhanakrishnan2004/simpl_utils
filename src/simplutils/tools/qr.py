"""QR code generation (needs segno: pip install simplutils[extras])."""
import io
from typing import Literal

from ..registry import FileResult, ToolError, tool

G = "QR"
_ERR = Literal["L", "M", "Q", "H"]


def _make(text: str, error: str):
    try:
        import segno
    except ImportError:
        raise ToolError("this tool needs segno: pip install simplutils[extras]")
    try:
        return segno.make(text, error=error, boost_error=False)
    except Exception as e:  # e.g. data too long for a QR code
        raise ToolError(f"cannot make QR code: {e}")


@tool("qr-generate", "QR Code (image)", G)
def qr_generate(text: str, kind: Literal["png", "svg"] = "png", scale: int = 8, error: _ERR = "M") -> FileResult:
    """Make a QR code image (PNG or SVG). `error` is the correction level: L, M, Q or H (more = bigger code)."""
    if not 1 <= scale <= 50:
        raise ToolError("scale must be 1-50")
    qr = _make(text, error)
    buf = io.BytesIO()
    qr.save(buf, kind=kind, scale=scale, border=4)
    mime = "image/png" if kind == "png" else "image/svg+xml"
    return FileResult(buf.getvalue(), f"qr.{kind}", mime)


@tool("qr-text", "QR Code (terminal)", G)
def qr_text(text: str, error: _ERR = "M") -> str:
    """Draw a QR code as text blocks you can scan straight from the terminal."""
    qr = _make(text, error)
    buf = io.StringIO()
    qr.terminal(out=buf, compact=True)
    return buf.getvalue().rstrip("\n")
