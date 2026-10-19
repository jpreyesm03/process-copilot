"""A Claude model behind the local `claude` CLI, used like a chat API (development and evals, no API key).

Each call is a fresh, stateless process: the whole conversation goes in, one reply comes out, as with an API.
Isolation is enforced, not requested: no built-in tools (`--tools ""`), no MCP servers, no user customisations,
an empty working directory, and our system prompt replaces the CLI's own. The model therefore cannot read
files, run code or see the eval keys; it only sees the messages our loop sends.

Tool use is prompted rather than native: tool schemas go in the system prompt, the model replies with a JSON
object ({"tool_calls": [...]} or {"content": "..."}) and this client turns it into the same LLMResponse the HTTP
client returns, so the loop, tools, guards and traces run unchanged.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from typing import Any

from dotenv import load_dotenv

from agentkit.llm import LLMResponse, ToolCall

PROTOCOL = """

## How to reply (you are behind an API)
You cannot run anything yourself. Each reply is ONE JSON object that a program reads:
- to request data: {"tool_calls": [{"name": "<tool>", "arguments": {...}}]}. The program runs every request
  and the next message contains the results.
- to answer the user: {"content": "<final answer>"}.
Reply with the JSON object only, no text around it.

## Requestable tools
"""


class ClaudeCLIClient:
    provider = "claude-cli"

    def __init__(self, model: str | None = None, timeout_s: float = 180):
        load_dotenv()
        self.model = model or os.getenv("LLM_MODEL", "haiku")
        self.timeout_s = timeout_s
        self.throttled_ms = 0  # same interface as the HTTP client; the CLI has no rate-limit waits to report
        self._workdir = tempfile.mkdtemp(prefix="llm_cli_")  # empty: nothing to read even if it tried
        self._n_calls = 0

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> LLMResponse:
        system = messages[0]["content"] + PROTOCOL + _render_tools(tools or [])
        cmd = ["claude", "-p", "--model", self.model, "--tools", "", "--system-prompt", system,
               "--output-format", "json", "--no-session-persistence", "--safe-mode", "--strict-mcp-config"]
        started = time.perf_counter()
        proc = subprocess.run(cmd, input=_render_conversation(messages[1:]), capture_output=True, text=True,
                              cwd=self._workdir, timeout=self.timeout_s)
        if proc.returncode != 0:
            raise RuntimeError(f"claude CLI failed: {proc.stderr.strip() or proc.stdout.strip()}"[:500])
        data = json.loads(proc.stdout)
        usage = data.get("usage") or {}
        reply = _parse_reply(data.get("result") or "")
        calls = []
        for c in reply.get("tool_calls") or []:
            self._n_calls += 1
            calls.append(ToolCall(f"call_{self._n_calls}", str(c.get("name")), json.dumps(c.get("arguments") or {})))
        content = None if calls else reply.get("content")
        raw = {"role": "assistant", "content": content}
        if calls:
            raw["tool_calls"] = [
                {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.arguments}} for c in calls
            ]
        return LLMResponse(
            content=content, tool_calls=calls,
            tokens_in=usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
            + usage.get("cache_read_input_tokens", 0),
            tokens_out=usage.get("output_tokens", 0),
            latency_ms=round((time.perf_counter() - started) * 1000), raw_message=raw,
            cost_usd=float(data.get("total_cost_usd") or 0),
        )


def _render_tools(tools: list[dict[str, Any]]) -> str:
    lines = []
    for t in tools:
        f = t["function"]
        lines.append(f"- {f['name']}: {f['description']}\n  arguments (JSON schema): {json.dumps(f['parameters'])}")
    return "\n".join(lines)


def _render_conversation(messages: list[dict[str, Any]]) -> str:
    """The conversation so far as one transcript (the CLI takes a single input), ending with a request to reply."""
    parts = []
    for m in messages:
        if m["role"] == "user":
            parts.append(f"USER:\n{m['content']}")
        elif m["role"] == "assistant":
            if m.get("tool_calls"):
                requested = [{"name": c["function"]["name"], "arguments": json.loads(c["function"]["arguments"])}
                             for c in m["tool_calls"]]
                parts.append(f"YOU REQUESTED:\n{json.dumps({'tool_calls': requested})}")
            if m.get("content"):
                parts.append(f"YOU SAID:\n{m['content']}")
        elif m["role"] == "tool":
            parts.append(f"RESULT ({m['tool_call_id']}):\n{m['content']}")
    parts.append("Reply now with one JSON object.")
    return "\n\n".join(parts)


def _parse_reply(text: str) -> dict[str, Any]:
    """The JSON object in the reply; plain text (no JSON) is taken as a final answer."""
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            obj = json.loads(text[start : end + 1])
            if isinstance(obj, dict) and ("tool_calls" in obj or "content" in obj):
                return obj
        except json.JSONDecodeError:
            pass
    return {"content": text.strip()}
