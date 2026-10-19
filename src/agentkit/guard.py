"""Output gate: every number in an answer must come from a tool result (or repeat the question); others are flagged.

"If 85 cans and 30 lids cost 100, what does a can cost?": the model may do the arithmetic, but that number was never
returned by the data, so it is marked [unverified] with a warning. The answer itself is not hidden (D11 revised):
withholding also hid correct answers that only mentioned an example number ("e.g. net 30").
"""

from __future__ import annotations

import re
from typing import Any

from agentkit import grounding


def ungrounded_numbers(answer: str | None, results: dict[str, Any], question: str) -> list[str]:
    return [n.text for n in grounding.check(answer or "", results, question) if n.status == "ungrounded"]


def flag_unverified(answer: str, unverified: list[str]) -> str:
    """Mark each unverified number in place and add a warning line (D11 revised: warn, never hide the answer)."""
    marked = answer
    for text in dict.fromkeys(unverified):  # once per distinct number, keeping order
        marked = re.sub(rf"(?<![\w.,]){re.escape(text)}(?![\w.,]?\d)", f"{text} [unverified]", marked)
    return (f"{marked}\n\n⚠ Not verified against the data: {', '.join(dict.fromkeys(unverified))}. "
            "These numbers did not come from any query result; treat them with caution.")
