import re
import unicodedata
from typing import Literal

from ..registry import tool

G = "Text"
Style = Literal["snake", "camel", "pascal", "kebab", "constant", "title", "upper", "lower"]


def _words(text: str):
    text = re.sub(r"[^0-9A-Za-z]+", " ", text)
    return re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+", text)


@tool("case-convert", "Case Converter", G)
def case_convert(text: str, style: Style = "snake") -> str:
    """Convert text between snake, camel, pascal, kebab and other cases."""
    w = _words(text)
    lo = [x.lower() for x in w]
    if style == "snake":
        return "_".join(lo)
    if style == "kebab":
        return "-".join(lo)
    if style == "constant":
        return "_".join(lo).upper()
    if style == "pascal":
        return "".join(x.capitalize() for x in lo)
    if style == "camel":
        return (lo[0] + "".join(x.capitalize() for x in lo[1:])) if lo else ""
    if style == "title":
        return " ".join(x.capitalize() for x in lo)
    if style == "upper":
        return text.upper()
    return text.lower()


@tool("slugify", "Slugify", G)
def slugify(text: str) -> str:
    """Make a URL-friendly slug."""
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


@tool("count", "Word & Char Count", G)
def count(text: str) -> str:
    """Count characters, words and lines."""
    lines = len(text.splitlines()) if text else 0
    return f"characters: {len(text)}\nwords: {len(text.split())}\nlines: {lines}"
