from datetime import datetime, timezone

from ..registry import ToolError, tool

G = "Time"


@tool("ts-to-date", "Timestamp → Date", G)
def ts_to_date(text: str) -> str:
    """Convert a Unix timestamp (seconds or milliseconds) to a date."""
    try:
        n = float(text.strip())
    except ValueError:
        raise ToolError("not a number")
    if abs(n) > 1e11:  # looks like milliseconds
        n /= 1000
    try:
        dt = datetime.fromtimestamp(n, timezone.utc)
    except (OverflowError, OSError, ValueError):
        raise ToolError("timestamp out of range")
    return f"UTC:   {dt.isoformat()}\nLocal: {dt.astimezone().isoformat()}"


@tool("date-to-ts", "Date → Timestamp", G)
def date_to_ts(text: str) -> str:
    """Convert an ISO date/time (e.g. 2026-01-31 14:30) to a Unix timestamp. Naive = UTC."""
    try:
        dt = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except ValueError:
        raise ToolError("use ISO format, e.g. 2026-01-31T14:30:00")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    s = dt.timestamp()
    return f"seconds: {int(s)}\nmilliseconds: {int(s * 1000)}"


@tool("now", "Current Time", G)
def now() -> str:
    """Show the current time as ISO and Unix timestamp."""
    n = datetime.now(timezone.utc)
    return f"UTC:  {n.isoformat()}\nUnix: {int(n.timestamp())}"
