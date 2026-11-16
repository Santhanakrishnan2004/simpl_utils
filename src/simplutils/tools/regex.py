import re

from ..registry import ToolError, tool

G = "Text"
MAX_MATCHES = 200


def _compile(pattern: str, ignore_case: bool, multiline: bool, dotall: bool):
    flags = (re.I if ignore_case else 0) | (re.M if multiline else 0) | (re.S if dotall else 0)
    try:
        return re.compile(pattern, flags)
    except re.error as e:
        raise ToolError(f"invalid regex: {e}")


@tool("regex-test", "Regex Tester", G)
def regex_test(text: str, pattern: str, ignore_case: bool = False, multiline: bool = False, dotall: bool = False) -> str:
    """Find all matches of a regex in the text, with positions and capture groups."""
    rx = _compile(pattern, ignore_case, multiline, dotall)
    matches = list(rx.finditer(text))
    if not matches:
        return "No matches."
    lines = [f"{len(matches)} match{'es' if len(matches) != 1 else ''}"]
    for i, m in enumerate(matches[:MAX_MATCHES], 1):
        lines.append(f"#{i}  [{m.start()}:{m.end()}]  {m.group(0)!r}")
        for n, g in enumerate(m.groups(), 1):
            lines.append(f"      group {n}: {g!r}")
        for name, g in m.groupdict().items():
            lines.append(f"      <{name}>: {g!r}")
    if len(matches) > MAX_MATCHES:
        lines.append(f"... {len(matches) - MAX_MATCHES} more not shown")
    return "\n".join(lines)


@tool("regex-replace", "Regex Replace", G)
def regex_replace(text: str, pattern: str, replacement: str, ignore_case: bool = False,
                  multiline: bool = False, dotall: bool = False) -> str:
    r"""Replace regex matches. In the replacement use \1, \2 or \g<name> for capture groups."""
    rx = _compile(pattern, ignore_case, multiline, dotall)
    try:
        return rx.sub(replacement, text)
    except (re.error, IndexError) as e:
        raise ToolError(f"invalid replacement: {e}")
