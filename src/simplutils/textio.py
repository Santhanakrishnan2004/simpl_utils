"""Reading text from files and stdin robustly (Windows editors and PowerShell often add a BOM or use UTF-16)."""
from __future__ import annotations

from .registry import ToolError


def decode_text(raw: bytes) -> str:
    """Decode bytes as text: UTF-8 (with or without BOM) or UTF-16 (with BOM). Raises ToolError otherwise."""
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return raw.decode("utf-16")  # also strips the BOM and detects endianness
        except UnicodeDecodeError:
            raise ToolError("the input looks like UTF-16 but could not be decoded")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ToolError("the input is not valid UTF-8 text (is it a binary file, or a legacy encoding?)")


def read_text_file(path: str) -> str:
    try:
        with open(path, "rb") as fh:
            return decode_text(fh.read())
    except OSError as e:
        raise ToolError(f"cannot read '{path}': {e}")
