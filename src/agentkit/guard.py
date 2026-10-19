"""Output gate: an answer is shown only if every number in it came from a tool result (or repeats the question).

This is what stops "if 85 cans and 30 lids cost 100, what does a can cost?": the model may do the arithmetic,
but those numbers were never returned by the data, so the answer is withheld.
"""

from __future__ import annotations

from typing import Any

from agentkit import grounding


def ungrounded_numbers(answer: str | None, results: dict[str, Any], question: str) -> list[str]:
    return [n.text for n in grounding.check(answer or "", results, question) if n.status == "ungrounded"]
