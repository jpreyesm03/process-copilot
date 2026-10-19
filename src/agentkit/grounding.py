"""Grounding check: every number in an answer must come from a tool result of the same run.

A number is
  grounded    if it matches a value in some tool result (after rounding, or in thousands/millions/%),
  derived     if it matches the sum, difference or ratio of two result values (e.g. "+34 days" = 40.0 - 6.3),
  ungrounded  otherwise: the model wrote a number no tool gave it.

Matching is deliberately lenient (half a unit of the last digit shown, or 0.5%, across thousands/millions/percent),
so a wrong number can occasionally pass as grounded, but a correct one is not failed.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from itertools import combinations
from typing import Any

# hyphens and spaces models write instead of ASCII ones (gpt-oss writes dates as 2018‑01‑02 with U+2011)
_NORMALIZE = str.maketrans({"‐": "-", "‑": "-", "‒": "-", " ": " ", " ": " ", " ": " "})
NUMBER = re.compile(
    r"(?<![\w.])[-+−]?(?:\d{1,3}(?:[, ]\d{3})+|\d+)(?:\.\d+)?\s*(?:%|[kKmMbB]n?\b|million\b|billion\b)?"
)
_MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?"
# tokens whose digits are not quantities: result ids, order lines, vendor ids, dates and times, ordinals
# ("50th percentile"), code in backticks, step numbers ("seq 6 -> 7")
IGNORE = re.compile(
    r"`[^`]*`|【[^】]*】|\[r\d+\]|\b\d{10}\s*[_-]\s*\d{5}\b|vendor\s*_?\s*ID[\s_]*\d+"
    r"|\b\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?\b|\b\d{1,2}:\d{2}\b|\b\d+(?:st|nd|rd|th)\b"
    rf"|\b(?:\d{{1,2}}[\s-]+)?{_MONTH}(?:\s+\d{{1,2}},?)?(?:[\s-]+\d{{4}})?\b"
    r"|\b(?:seq|steps?|cycle|r)\s*\d+(?:\s*(?:→|->|–|-|to|and)\s*\d+)?",
    re.IGNORECASE,
)
# a bare small integer is a count ("top 5", "2 waits"), unless a unit follows ("5 days")
_UNIT_AFTER = re.compile(r"\s*(?:days?|d\b|%|€|eur|lines?|hours?|weeks?|months?)", re.IGNORECASE)
SCALE = {"k": 1e3, "m": 1e6, "mn": 1e6, "million": 1e6, "b": 1e9, "bn": 1e9, "billion": 1e9}
MAX_PAIRS_POOL = 400  # differences/ratios are only searched when the pool is small enough


@dataclass
class Number:
    text: str
    value: float
    tol: float  # half a unit of the last digit shown: "16.3M" -> 50,000
    status: str = "ungrounded"


def extract_numbers(text: str) -> list[Number]:
    """Numbers stated in a text, with units applied (16.3M -> 16_300_000). Bare integers up to 10 are skipped
    (counts like "top 5"), unless a unit follows them ("10 days")."""
    cleaned = IGNORE.sub(" ", text.translate(_NORMALIZE))
    out = []
    for m in NUMBER.finditer(cleaned):
        raw = m.group(0).strip()
        unit = re.search(r"(%|[kKmMbB]n?|million|billion)$", raw)
        digits = (raw[: unit.start()].strip() if unit else raw).replace("−", "-").replace(",", "").replace(" ", "")
        try:
            value = float(digits)
        except ValueError:
            continue
        scale = SCALE.get(unit.group(1).lower(), 1) if unit else 1
        if value.is_integer() and abs(value) <= 10 and not unit and not _UNIT_AFTER.match(cleaned, m.end()):
            continue
        out.append(Number(raw, value * scale, 0.5 * 10 ** -_decimals(digits) * scale))
    return out


def collect_values(payload: Any) -> list[float]:
    """Every number inside a tool result (nested dicts/lists, numeric strings included)."""
    found: list[float] = []

    def walk(x: Any) -> None:
        if isinstance(x, bool) or x is None:
            return
        if isinstance(x, int | float):
            if math.isfinite(x):
                found.append(float(x))
        elif isinstance(x, str):
            try:
                found.append(float(x))
            except ValueError:
                pass
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list | tuple):
            for v in x:
                walk(v)

    walk(payload)
    return found


def _decimals(text: str) -> int:
    m = re.search(r"\.(\d+)", text)
    return len(m.group(1)) if m else 0


def _matches(stated: Number, candidate: float) -> bool:
    """True if the stated number is the candidate as written: rounded to the digits shown (or within 0.5%),
    possibly as a percentage of a share (65.3% for 0.653) or in thousands/millions without a unit word."""
    variants = (candidate, candidate * 100, candidate / 1e3, candidate / 1e6, candidate / 1e9)
    return any(abs(stated.value - c) <= max(stated.tol, 0.005 * abs(c)) for c in variants if c)


def check(answer: str, results: dict[str, Any], question: str = "") -> list[Number]:
    """Classify every number in the answer against all tool results of the run. Numbers from the question may be
    repeated (grounded) but not computed with: arithmetic on user-supplied numbers is not an answer from the data."""
    pool = sorted(set(collect_values(results)))
    echoed = [n.value for n in extract_numbers(question)]
    numbers = extract_numbers(answer or "")
    for n in numbers:
        if any(_matches(n, v) for v in pool + echoed):
            n.status = "grounded"
        elif len(pool) <= MAX_PAIRS_POOL and any(
            _matches(n, abs(a - b)) or _matches(n, a + b) or (b and _matches(n, a / b)) or (a and _matches(n, b / a))
            for a, b in combinations(pool, 2)
        ):
            n.status = "derived"
    return numbers
