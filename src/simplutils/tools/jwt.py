import base64
import json
from datetime import datetime, timezone

from ..registry import ToolError, tool


def _part(s: str) -> dict:
    s += "=" * (-len(s) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(s))
    except Exception as e:
        raise ToolError(f"invalid JWT segment: {e}")


@tool("jwt-decode", "JWT Decode", "Security")
def jwt_decode(text: str) -> str:
    """Decode a JWT's header and payload (signature is NOT verified)."""
    parts = text.strip().split(".")
    if len(parts) != 3:
        raise ToolError("a JWT has 3 dot-separated parts")
    header, payload = _part(parts[0]), _part(parts[1])
    out = {"header": header, "payload": payload}
    now = datetime.now(timezone.utc).timestamp()
    for claim in ("iat", "nbf", "exp"):
        v = payload.get(claim)
        if isinstance(v, (int, float)):
            out.setdefault("times", {})[claim] = datetime.fromtimestamp(v, timezone.utc).isoformat()
    exp = payload.get("exp")
    if isinstance(exp, (int, float)):
        out["expired"] = exp < now
    return json.dumps(out, indent=2, ensure_ascii=False)
