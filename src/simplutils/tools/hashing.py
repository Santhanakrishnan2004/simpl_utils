import hashlib
import hmac
from typing import Literal

from ..registry import tool

G = "Hashing"
Algo = Literal["sha256", "sha512", "sha1", "md5"]


@tool("hash", "Hash", G)
def hash_text(text: str, algo: Algo = "sha256") -> str:
    """Compute a hash digest of the text."""
    return hashlib.new(algo, text.encode("utf-8")).hexdigest()


@tool("hmac", "HMAC", G)
def hmac_text(text: str, key: str, algo: Algo = "sha256") -> str:
    """Compute an HMAC of the text with a secret key."""
    return hmac.new(key.encode("utf-8"), text.encode("utf-8"), algo).hexdigest()
