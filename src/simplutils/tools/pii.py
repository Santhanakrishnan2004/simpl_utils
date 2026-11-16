"""Find and redact personal data and secrets in text, entirely offline.

Detection is heuristic (regex + checksums such as Luhn / Verhoeff / IBAN mod-97). It catches the
common cases but is NOT a guarantee - always review before sharing sensitive text.
"""
from __future__ import annotations

import hashlib
import logging
import re
import secrets
from collections import Counter
from dataclasses import dataclass
from typing import Callable, List, Optional, Set, Tuple

from typing import Literal

from ..registry import ToolError, tool

G = "Privacy (PII)"
log = logging.getLogger("simplutils")


# ---------------------------------------------------------------- checksums
def luhn_ok(value: str) -> bool:
    digits = [int(c) for c in re.sub(r"\D", "", value)]
    if not 13 <= len(digits) <= 19 or len(set(digits)) == 1:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    return total % 10 == 0


_D = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5], [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
      [3, 4, 0, 1, 2, 8, 9, 5, 6, 7], [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
      [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3], [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
      [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]]
_P = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4], [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
      [8, 9, 1, 6, 0, 4, 3, 5, 2, 7], [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
      [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]]
_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def verhoeff_ok(value: str) -> bool:
    c = 0
    for i, ch in enumerate(reversed(re.sub(r"\D", "", value))):
        c = _D[c][_P[i % 8][int(ch)]]
    return c == 0


def verhoeff_check_digit(number: str) -> str:
    c = 0
    for i, ch in enumerate(reversed(number)):
        c = _D[c][_P[(i + 1) % 8][int(ch)]]
    return str(_INV[c])


def iban_ok(value: str) -> bool:
    s = re.sub(r"\s", "", value).upper()
    if not 15 <= len(s) <= 34:
        return False
    moved = s[4:] + s[:4]
    num = "".join(str(int(c, 36)) for c in moved)
    return int(num) % 97 == 1


# ---------------------------------------------------------------- detectors
@dataclass
class Finding:
    kind: str
    start: int
    end: int
    value: str


# (kind, regex, capture group to redact, validator). Order = priority: earlier wins on overlap.
_DETECTORS: List[Tuple[str, "re.Pattern[str]", int, Optional[Callable[[str], bool]]]] = [
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"), 0, None),
    ("aws-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), 0, None),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"), 0, None),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), 0, None),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), 0, None),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]*"), 0, None),
    ("bearer-token", re.compile(r"\bBearer\s+([A-Za-z0-9._~+/=-]{16,})"), 1, None),
    ("url-password", re.compile(r"(?<=://)[^\s:/@]+:([^\s@/]+)(?=@)"), 1, None),
    ("password", re.compile(
        r"(?i)\b(?:password|passwd|pwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)\b[\"']?\s*[:=]\s*[\"']?([^\s\"',;]{4,})"),
     1, None),
    ("credit-card", re.compile(r"(?<![\d-])(?:\d[ -]?){12,18}\d(?![\d-])"), 0, luhn_ok),
    ("iban", re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,3})?\b"), 0, iban_ok),
    ("aadhaar", re.compile(r"(?<!\d)[2-9]\d{3}[ -]?\d{4}[ -]?\d{4}(?!\d)"), 0, verhoeff_ok),
    ("ssn", re.compile(r"\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b"), 0, None),
    ("pan", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), 0, None),
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}"), 0, None),
    # not part of a longer dotted number (version strings like 1.2.3.4.5)
    ("ip-address", re.compile(
        r"(?<![\w.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?!\w|\.\d)"), 0, None),
    ("phone", re.compile(
        r"(?<![\w.])(?:\+91[ -]?|0)?[6-9]\d{4}[ -]?\d{5}(?!\w)"                      # India mobile
        r"|(?<![\w.])(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\w)"            # US / Canada
        r"|(?<![\w.])\+\d{1,3}[ -]?\d{1,4}(?:[ -]?\d{2,4}){2,4}(?!\w)"), 0, None),    # other international
]

KINDS: List[str] = [d[0] for d in _DETECTORS]
_FULL_MASK = {"private-key", "aws-key", "github-token", "slack-token", "google-api-key", "jwt",
              "bearer-token", "url-password", "password"}  # secrets are never partially revealed


def detect(text: str, kinds: Optional[Set[str]] = None) -> List[Finding]:
    """Return non-overlapping findings sorted by position.

    `kinds` limits what is *reported*. Every detector still claims the text it matches, so a type
    you switched off keeps suppressing weaker guesses (e.g. excluding "credit-card" does not make
    the same digits show up as a "phone", and "user:pass@host" is not mistaken for an email).
    """
    taken = bytearray(len(text))
    found: List[Finding] = []
    for kind, rx, group, check in _DETECTORS:
        report = kinds is None or kind in kinds
        for m in rx.finditer(text):
            s, e = m.span(group)
            if s < 0 or any(taken[s:e]):
                continue
            value = text[s:e]
            if check is not None and not check(value):
                continue
            taken[s:e] = b"\x01" * (e - s)
            if report:
                found.append(Finding(kind, s, e, value))
    found.sort(key=lambda f: f.start)
    return found


def _parse_kinds(spec: str, exclude: str) -> Optional[Set[str]]:
    def names(s: str) -> Set[str]:
        out = {x.strip().lower() for x in s.split(",") if x.strip()}
        bad = out - set(KINDS)
        if bad:
            raise ToolError(f"unknown type(s): {', '.join(sorted(bad))}. See: simplutils pii-types")
        return out

    only, skip = names(spec), names(exclude)
    if not only and not skip:
        return None
    return (only or set(KINDS)) - skip


def _replacement(f: Finding, mode: str, salt: bytes) -> str:
    tag = f.kind.upper()
    if mode == "label" or f.kind == "private-key":
        return f"[{tag}]"
    if mode == "hash":
        return f"[{tag}#{hashlib.sha256(salt + f.value.encode()).hexdigest()[:8]}]"
    if f.kind in _FULL_MASK:
        return "********"
    idx = [i for i, c in enumerate(f.value) if c.isalnum()]
    keep = set(idx[-4:]) if len(idx) > 4 else set()
    return "".join(c if (not c.isalnum() or i in keep) else "*" for i, c in enumerate(f.value))


def _log_summary(action: str, findings: List[Finding]) -> None:
    counts = dict(Counter(f.kind for f in findings))
    log.info("%s: %d finding(s) %s", action, len(findings), counts)  # counts only, never values


@tool("pii-redact", "PII Redact", G)
def pii_redact(text: str, mode: Literal["label", "mask", "hash"] = "label", only: str = "", exclude: str = "") -> str:
    """Replace emails, phones, cards, IDs, API keys and passwords with safe placeholders (runs offline)."""
    findings = detect(text, _parse_kinds(only, exclude))
    _log_summary("pii-redact", findings)
    salt = secrets.token_bytes(16)  # random per run: same value -> same token within this text only
    out, pos = [], 0
    for f in findings:
        out.append(text[pos:f.start])
        out.append(_replacement(f, mode, salt))
        pos = f.end
    out.append(text[pos:])
    return "".join(out)


def _preview(v: str) -> str:
    v = " ".join(v.split())
    return v[:2] + "***" if len(v) > 4 else "***"


@tool("pii-scan", "PII Scan (report)", G)
def pii_scan(text: str, only: str = "", exclude: str = "") -> str:
    """Report what personal data / secrets the text seems to contain, without printing the values."""
    findings = detect(text, _parse_kinds(only, exclude))
    _log_summary("pii-scan", findings)
    if not findings:
        return "Nothing detected. (Checks are heuristic - this is not a guarantee.)"
    counts = Counter(f.kind for f in findings)
    lines = [f"Found {len(findings)} potential item(s) of {len(counts)} type(s)", "", "Summary"]
    lines += [f"  {k:<15} {n}" for k, n in counts.most_common()]
    lines += ["", "Details (values are hidden)"]
    for f in findings[:500]:
        line_no = text.count("\n", 0, f.start) + 1
        lines.append(f"  line {line_no:<5} {f.kind:<15} {_preview(f.value)}")
    if len(findings) > 500:
        lines.append(f"  ... {len(findings) - 500} more")
    return "\n".join(lines)


@tool("pii-types", "PII Types", G)
def pii_types() -> str:
    """List everything the PII tools can detect (use these names with --only / --exclude)."""
    return "\n".join(KINDS)
