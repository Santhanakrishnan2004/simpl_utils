import base64
import binascii
import html
import urllib.parse

from ..registry import ToolError, tool

G = "Encoding"


@tool("b64-encode", "Base64 Encode", G)
def b64_encode(text: str, urlsafe: bool = False) -> str:
    """Encode text as Base64."""
    raw = text.encode("utf-8")
    return (base64.urlsafe_b64encode(raw) if urlsafe else base64.b64encode(raw)).decode()


@tool("b64-decode", "Base64 Decode", G)
def b64_decode(text: str, urlsafe: bool = False) -> str:
    """Decode Base64 text (padding optional)."""
    s = "".join(text.split())
    s += "=" * (-len(s) % 4)
    try:
        raw = base64.urlsafe_b64decode(s) if urlsafe else base64.b64decode(s, validate=True)
        return raw.decode("utf-8")
    except (binascii.Error, ValueError) as e:
        raise ToolError(f"invalid Base64 (try the urlsafe option?): {e}")


@tool("url-encode", "URL Encode", G)
def url_encode(text: str, plus: bool = False) -> str:
    """Percent-encode text for use in a URL."""
    return urllib.parse.quote_plus(text) if plus else urllib.parse.quote(text, safe="")


@tool("url-decode", "URL Decode", G)
def url_decode(text: str, plus: bool = False) -> str:
    """Decode percent-encoded text."""
    return urllib.parse.unquote_plus(text) if plus else urllib.parse.unquote(text)


@tool("hex-encode", "Hex Encode", G)
def hex_encode(text: str) -> str:
    """Convert text to hexadecimal."""
    return text.encode("utf-8").hex()


@tool("hex-decode", "Hex Decode", G)
def hex_decode(text: str) -> str:
    """Convert hexadecimal back to text."""
    try:
        return bytes.fromhex("".join(text.split())).decode("utf-8")
    except ValueError as e:
        raise ToolError(f"invalid hex: {e}")


@tool("html-escape", "HTML Escape", G)
def html_escape(text: str) -> str:
    """Escape &, <, > and quotes as HTML entities."""
    return html.escape(text)


@tool("html-unescape", "HTML Unescape", G)
def html_unescape(text: str) -> str:
    """Turn HTML entities back into characters."""
    return html.unescape(text)
