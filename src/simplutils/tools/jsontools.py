import json

from ..registry import ToolError, tool

G = "JSON"


def _load(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ToolError(f"invalid JSON: {e}")


@tool("json-format", "JSON Format", G)
def json_format(text: str, indent: int = 2, sort_keys: bool = False) -> str:
    """Validate and pretty-print JSON."""
    return json.dumps(_load(text), indent=indent, sort_keys=sort_keys, ensure_ascii=False)


@tool("json-minify", "JSON Minify", G)
def json_minify(text: str) -> str:
    """Validate and compact JSON onto one line."""
    return json.dumps(_load(text), separators=(",", ":"), ensure_ascii=False)
