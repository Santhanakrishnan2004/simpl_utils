import difflib
import json
from typing import Any, List

from ..registry import ToolError, tool
from ..textio import decode_text

G = "Compare"


def _two(files: List[bytes]) -> List[str]:
    if len(files) != 2:
        raise ToolError("give exactly two files: first the 'before', then the 'after'")
    out = []
    for f in files:
        try:
            out.append(decode_text(f))  # handles BOM / UTF-16
        except ToolError:
            out.append(f.decode("utf-8", errors="replace"))  # diff stays usable on odd encodings
    return out


@tool("diff", "Text Diff", G)
def text_diff(files: List[bytes], context: int = 3, ignore_whitespace: bool = False) -> str:
    """Compare two text files and show a unified diff (first file = before, second = after)."""
    a, b = _two(files)
    if context < 0:
        raise ToolError("context cannot be negative")
    la, lb = a.splitlines(), b.splitlines()
    if ignore_whitespace:
        la, lb = [" ".join(x.split()) for x in la], [" ".join(x.split()) for x in lb]
    out = list(difflib.unified_diff(la, lb, "before", "after", n=context, lineterm=""))
    return "\n".join(out) if out else "No differences."


def _short(v: Any) -> str:
    s = json.dumps(v, ensure_ascii=False)
    return s if len(s) <= 80 else s[:77] + "..."


def _walk(a: Any, b: Any, path: str, out: List[str]) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            p = f"{path}.{k}" if path else str(k)
            if k not in b:
                out.append(f"- {p}: {_short(a[k])}")
            elif k not in a:
                out.append(f"+ {p}: {_short(b[k])}")
            else:
                _walk(a[k], b[k], p, out)
    elif isinstance(a, list) and isinstance(b, list):
        for i in range(max(len(a), len(b))):
            p = f"{path}[{i}]"
            if i >= len(b):
                out.append(f"- {p}: {_short(a[i])}")
            elif i >= len(a):
                out.append(f"+ {p}: {_short(b[i])}")
            else:
                _walk(a[i], b[i], p, out)
    elif a != b or type(a) is not type(b):
        out.append(f"~ {path or '(root)'}: {_short(a)} -> {_short(b)}")


@tool("json-diff", "JSON Diff", G)
def json_diff(files: List[bytes]) -> str:
    """Compare two JSON files structurally (+ added, - removed, ~ changed). First = before, second = after."""
    a, b = _two(files)
    try:
        ja, jb = json.loads(a), json.loads(b)
    except json.JSONDecodeError as e:
        raise ToolError(f"invalid JSON: {e}")
    out: List[str] = []
    _walk(ja, jb, "", out)
    return "\n".join(out) if out else "No differences."
