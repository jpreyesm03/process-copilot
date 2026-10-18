"""Generic tool plumbing: typed arguments, JSON schemas for the model, and a result store for citations."""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ValidationError


@dataclass
class Tool:
    name: str
    description: str  # tells the model WHEN to use it, not only what it does
    args_model: type[BaseModel]
    fn: Callable[..., dict[str, Any]]

    def schema(self) -> dict[str, Any]:
        """OpenAI-compatible function schema (also accepted by Groq, Gemini, Ollama)."""
        params = self.args_model.model_json_schema()
        params.pop("title", None)
        return {"type": "function",
                "function": {"name": self.name, "description": self.description, "parameters": params}}


@dataclass
class ResultStore:
    """Keeps every full tool result of a run, so answers can cite result ids and numbers can be checked."""
    results: dict[str, Any] = field(default_factory=dict)

    def put(self, payload: Any) -> str:
        result_id = f"r{len(self.results) + 1}"
        self.results[result_id] = payload
        return result_id


def call_tool(tools: dict[str, Tool], name: str, raw_args: str | dict, store: ResultStore) -> dict[str, Any]:
    """Validate arguments and run a tool. Errors come back as text the model can act on, never as exceptions."""
    tool = tools.get(name)
    if tool is None:
        return {"ok": False, "error": f"Unknown tool '{name}'. Available: {', '.join(tools)}."}
    try:
        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        parsed = tool.args_model.model_validate(args or {})
    except (json.JSONDecodeError, ValidationError) as exc:
        return {"ok": False, "error": f"Invalid arguments for {name}: {exc}"}
    try:
        result = tool.fn(**parsed.model_dump())
    except Exception as exc:  # a tool failure is information for the model, not a crash of the run
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if result.get("ok", True):
        result["result_id"] = store.put(result.pop("_full", result))
    return result
