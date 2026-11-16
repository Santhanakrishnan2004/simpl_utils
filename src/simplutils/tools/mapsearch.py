"""Search a map (JSON object/list, or YAML) without writing a snippet: find, count, get, tally."""
import json
import re
from collections import Counter
from typing import Any, Callable, Iterator, List, Literal, Tuple

from ..registry import ToolError, tool

G = "Data"

_PATH_TOKEN = re.compile(r'\["((?:[^"\\]|\\.)*)"\]|\[(-?\d+|\*)\]|([^.\[\]]+)')


def _load(text: Any) -> Any:
    if isinstance(text, (dict, list)):  # library use: pass your dict/list directly
        return text
    try:
        data = json.loads(text)
    except json.JSONDecodeError as json_err:
        try:
            import yaml
        except ImportError:
            raise ToolError(f"input is not valid JSON ({json_err}). "
                            "To also read YAML: pip install \"simplutils[extras]\"")
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as e:
            raise ToolError(f"input is neither valid JSON nor valid YAML: {e}")
    except RecursionError:
        raise ToolError("input is nested too deeply")
    if not isinstance(data, (dict, list)):
        raise ToolError("input must be a JSON object or list (a map to search in)")
    return data


def _fmt_key(path: str, key: Any) -> str:
    k = str(key)
    if any(c in k for c in '.[]"') or k == "" or k == "*":
        return f"{path}[{json.dumps(k, ensure_ascii=False)}]"
    return f"{path}.{k}" if path else k


def _walk(node: Any, path: str = "") -> Iterator[Tuple[str, Any, Any, bool]]:
    """Yield (path, key, value, is_leaf) for every entry, in one pass (iterative, no recursion limit)."""
    stack: List[Tuple[Any, str]] = [(node, path)]
    while stack:
        cur, p = stack.pop()
        if isinstance(cur, dict):
            items = [(k, v, _fmt_key(p, k)) for k, v in cur.items()]
        elif isinstance(cur, list):
            items = [(i, v, f"{p}[{i}]") for i, v in enumerate(cur)]
        else:
            continue
        for k, v, kp in items:
            leaf = not isinstance(v, (dict, list))
            yield kp, k, v, leaf
        stack.extend((v, kp) for k, v, kp in reversed(items) if isinstance(v, (dict, list)))


def _text(v: Any) -> str:
    return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)


def _short(v: Any, n: int = 80) -> str:
    s = json.dumps(v, ensure_ascii=False)
    return s if len(s) <= n else s[: n - 3] + "..."


def _matcher(query: str, mode: str, ignore_case: bool) -> Callable[[str], bool]:
    if mode == "regex":
        try:
            rx = re.compile(query, re.IGNORECASE if ignore_case else 0)
        except re.error as e:
            raise ToolError(f"invalid regex: {e}")
        return lambda s: rx.search(s) is not None
    q = query.lower() if ignore_case else query
    norm = (lambda s: s.lower()) if ignore_case else (lambda s: s)
    if mode == "contains":
        return lambda s: q in norm(s)
    return lambda s: norm(s) == q


def _get(node: Any, path: str) -> List[Any]:
    tokens = []
    pos = 0
    path = path.strip()
    while pos < len(path):
        if path[pos] == ".":
            pos += 1
            continue
        m = _PATH_TOKEN.match(path, pos)
        if not m:
            raise ToolError(f"cannot read the path near '{path[pos:]}'. Example: users[0].name or users[*].email")
        quoted, index, name = m.groups()
        if quoted is not None:
            tokens.append(("key", json.loads(f'"{quoted}"')))
        elif index is not None:
            tokens.append(("star", None) if index == "*" else ("index", int(index)))
        else:
            tokens.append(("star", None) if name == "*" else ("key", name))
        pos = m.end()
    if not tokens:
        raise ToolError("give a path, e.g. users[0].name")
    current = [(node, "")]
    for kind, val in tokens:
        nxt = []
        for n, p in current:
            if kind == "star":
                if isinstance(n, dict):
                    nxt.extend((v, _fmt_key(p, k)) for k, v in n.items())
                elif isinstance(n, list):
                    nxt.extend((v, f"{p}[{i}]") for i, v in enumerate(n))
            elif kind == "index":
                if isinstance(n, list) and -len(n) <= val < len(n):
                    nxt.append((n[val], f"{p}[{val}]"))
            else:
                if isinstance(n, dict) and val in n:
                    nxt.append((n[val], _fmt_key(p, val)))
                elif isinstance(n, list) and val.lstrip("-").isdigit() and -len(n) <= int(val) < len(n):
                    nxt.append((n[int(val)], f"{p}[{int(val)}]"))
        if not nxt:
            raise ToolError(f"nothing found at '{path}' (stopped at '{val if kind != 'star' else '*'}')")
        current = nxt
    return [v for v, _ in current]


@tool("map-search", "Map Search", G)
def map_search(
    text: str,
    action: Literal["find", "count", "get", "tally"] = "find",
    by: Literal["key", "value"] = "key",
    query: str = "",
    match: Literal["exact", "contains", "regex"] = "exact",
    ignore_case: bool = False,
    limit: int = 100,
) -> str:
    """Search a JSON/YAML map: find or count keys/values, get a value by path, tally values of a key."""
    if not query:
        raise ToolError("tell me what to look for: query (a key or value to search; for 'get' a path like a.b[0].c)")
    if limit < 1:
        raise ToolError("limit must be at least 1")
    data = _load(text)

    if action == "get":
        found = _get(data, query)
        return json.dumps(found[0] if len(found) == 1 and "*" not in query else found,
                          indent=2, ensure_ascii=False)

    is_match = _matcher(query, match, ignore_case)
    if action == "tally" and by != "key":
        raise ToolError("tally counts the values of a key, so use by=key (e.g. query=city)")

    hits: List[Tuple[str, Any]] = []  # (path, value)
    for path, key, value, leaf in _walk(data):
        if by == "key":
            if is_match(str(key)):
                hits.append((path, value))
        elif leaf and is_match(_text(value)):
            hits.append((path, value))

    what = "keys" if by == "key" else "values"
    if action == "count":
        return str(len(hits))
    if not hits:
        return "No matches."
    if action == "tally":
        counts = Counter(json.dumps(v, sort_keys=True, ensure_ascii=False) for _, v in hits)
        rows = counts.most_common(limit)
        width = max(len(r[0]) for r in rows)
        out = [f"{v:<{width}}  {n}" for v, n in rows]
        if len(counts) > limit:
            out.append(f"... and {len(counts) - limit} more distinct values")
        return f"{len(hits)} match(es) across {len(counts)} distinct value(s)\n" + "\n".join(out)

    shown = [f"{p}: {_short(v)}" for p, v in hits[:limit]]
    if len(hits) > limit:
        shown.append(f"... and {len(hits) - limit} more (raise limit to see them)")
    return f"{len(hits)} matching {what}\n" + "\n".join(shown)
