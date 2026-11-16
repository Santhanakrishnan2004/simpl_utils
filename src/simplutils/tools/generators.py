import random
import secrets
import string
import uuid
from typing import Literal

from ..registry import ToolError, tool

G = "Generators"


@tool("uuid", "UUID Generator", G)
def uuid_gen(count: int = 1) -> str:
    """Generate random UUIDs (v4)."""
    if not 1 <= count <= 1000:
        raise ToolError("count must be 1-1000")
    return "\n".join(str(uuid.uuid4()) for _ in range(count))


_CHARSETS = {
    "alnum": string.ascii_letters + string.digits,
    "letters": string.ascii_letters,
    "lower": string.ascii_lowercase,
    "upper": string.ascii_uppercase,
    "digits": string.digits,
    "hex": "0123456789abcdef",
}
_WORDS = ("lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut "
          "labore et dolore magna aliqua enim ad minim veniam quis nostrud exercitation ullamco laboris "
          "nisi aliquip ex ea commodo consequat duis aute irure in reprehenderit voluptate velit esse "
          "cillum fugiat nulla pariatur excepteur sint occaecat cupidatat non proident sunt culpa qui "
          "officia deserunt mollit anim id est laborum").split()
_RNG = random.SystemRandom()  # OS randomness; fast for long strings


def _words(length: int) -> str:
    parts, size = [], -1  # size = length of " ".join(parts)
    while size < length:
        w = _RNG.choice(_WORDS)
        parts.append(w)
        size += len(w) + 1
    s = " ".join(parts)[:length]
    return s[:-1] + _RNG.choice(string.ascii_lowercase) if s.endswith(" ") else s


@tool("random-text", "Random Text", G)
def random_text(
    length: int = 32,
    charset: Literal["alnum", "letters", "lower", "upper", "digits", "hex", "words"] = "alnum",
    count: int = 1,
    custom: str = "",
) -> str:
    """Generate random text of an exact length (letters, digits, hex, lorem-style words or your own characters)."""
    if not 1 <= length <= 1_000_000:
        raise ToolError("length must be 1-1,000,000")
    if not 1 <= count <= 1000:
        raise ToolError("count must be 1-1000")
    if length * count > 5_000_000:
        raise ToolError("length x count is too large (max 5,000,000 characters in total)")
    if custom:
        alphabet = "".join(dict.fromkeys(custom))  # unique, keeps order; overrides charset
        return "\n".join("".join(_RNG.choices(alphabet, k=length)) for _ in range(count))
    if charset == "words":
        return "\n".join(_words(length) for _ in range(count))
    alphabet = _CHARSETS[charset]
    return "\n".join("".join(_RNG.choices(alphabet, k=length)) for _ in range(count))


@tool("password", "Password Generator", G)
def password(length: int = 16, no_symbols: bool = False) -> str:
    """Generate a cryptographically secure random password."""
    if not 4 <= length <= 256:
        raise ToolError("length must be 4-256")
    alphabet = string.ascii_letters + string.digits + ("" if no_symbols else "!@#$%^&*-_=+?")
    return "".join(secrets.choice(alphabet) for _ in range(length))
