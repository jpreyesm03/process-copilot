"""The agent loop: the model decides the next step; this code sets the limits (steps, repeats, read-only tools)."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from agentkit.tools import ResultStore, Tool, call_tool
from agentkit.trace import Tracer

MAX_STEPS = 10
MAX_RUN_TOKENS = 30_000  # cost cap per question (C2): about 10x a normal run
MAX_RESULT_CHARS = 8000  # one tool result in the model's context (C2 cost)


@dataclass
class AgentResult:
    answer: str | None
    stop_reason: str  # answered | max_steps | loop_detected | token_budget
    run_id: str
    steps: list[dict[str, Any]] = field(default_factory=list)  # the trajectory: what the agent did, in order
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    store: ResultStore = field(default_factory=ResultStore)
    blocked: str | None = None  # set when a guard withheld the answer (the model's text stays in the trace)


def _compact(result: dict[str, Any]) -> str:
    text = json.dumps(result, default=str)
    if len(text) > MAX_RESULT_CHARS:
        text = text[:MAX_RESULT_CHARS] + ' ..."[truncated: ask for fewer rows or aggregate]"'
    return text


def run_agent(question: str, *, llm, tools: dict[str, Tool], system_prompt: str, tracer: Tracer | None = None,
              prompt_version: str = "v1", max_steps: int = MAX_STEPS,
              max_tokens: int = MAX_RUN_TOKENS) -> AgentResult:
    tracer = tracer or Tracer(None)
    run_id = tracer.new_run()
    started_at, t0 = datetime.now(), time.perf_counter()
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt},
                                      {"role": "user", "content": question}]
    schemas = [t.schema() for t in tools.values()]
    store = ResultStore()
    out = AgentResult(answer=None, stop_reason="max_steps", run_id=run_id, store=store)
    seen_calls: set[tuple[str, str]] = set()

    for step in range(1, max_steps + 1):
        resp = llm.chat(messages, schemas)
        out.tokens_in += resp.tokens_in
        out.tokens_out += resp.tokens_out
        tracer.step(run_id, step, "llm", tokens_in=resp.tokens_in, tokens_out=resp.tokens_out,
                    latency_ms=resp.latency_ms, content=resp.content)

        if not resp.tool_calls:  # the model decided it has enough to answer
            out.answer, out.stop_reason = resp.content, "answered"
            break
        if out.tokens_in + out.tokens_out >= max_tokens:  # still working but over budget: stop paying
            out.stop_reason = "token_budget"
            break

        messages.append(resp.raw_message)
        repeated = False
        for call in resp.tool_calls:
            key = (call.name, call.arguments)
            repeated = repeated or key in seen_calls
            seen_calls.add(key)
            result = call_tool(tools, call.name, call.arguments, store)
            out.steps.append({"step": step, "tool": call.name, "args": call.arguments,
                              "ok": result.get("ok", True), "result_id": result.get("result_id"),
                              "error": result.get("error")})
            tracer.step(run_id, step, "tool", tool_name=call.name, args=call.arguments,
                        result_id=result.get("result_id"), ok=result.get("ok", True), error=result.get("error"))
            messages.append({"role": "tool", "tool_call_id": call.id, "content": _compact(result)})
        if repeated:  # same tool, same arguments again: it is going in circles
            out.stop_reason = "loop_detected"
            break

    out.latency_ms = round((time.perf_counter() - t0) * 1000)
    tracer.finish(run_id, question, getattr(llm, "model", "unknown"), prompt_version, started_at, out.latency_ms,
                  out.tokens_in, out.tokens_out, len(out.steps), out.stop_reason, out.answer)
    return out
