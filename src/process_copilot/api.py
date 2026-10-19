"""HTTP API for the Process Copilot agent.

Run: uvicorn process_copilot.api:app --port 8000   → docs at http://localhost:8000/docs
"""
from __future__ import annotations

import os
import threading
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from agentkit.limits import UsageLimiter
from process_copilot.agent import OUT_OF_SCOPE_ANSWER, ask, build_agent, topic_gate

app = FastAPI(title="Process Copilot", description="Ask questions about the purchase-to-pay process.")
_lock = threading.Lock()  # one DuckDB connection and one agent run at a time (enough for a demo)
limiter = UsageLimiter(per_client_per_hour=int(os.getenv("LIMIT_PER_CLIENT_HOUR", "20")),
                       per_day=int(os.getenv("LIMIT_PER_DAY", "300")))


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000,
                          examples=["Why did order line 4507000229_00010 take so long?"])


class Step(BaseModel):
    step: int
    tool: str
    args: str
    ok: bool
    result_id: str | None = None
    error: str | None = None


class AskResponse(BaseModel):
    answer: str | None
    stop_reason: str
    steps: list[Step]
    tokens: int
    latency_ms: int
    run_id: str
    flagged: str | None = None  # numbers the output gate could not verify (marked [unverified] in the answer)


@lru_cache(maxsize=1)
def _agent():
    return build_agent()


@lru_cache(maxsize=1)
def _gate():
    """The topic gate is on when TOPIC_MODEL is set (needs its provider's key); off in tests and local runs."""
    return topic_gate() if os.getenv("TOPIC_MODEL") else None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(req: AskRequest, request: Request) -> AskResponse:
    refused = limiter.check(request.client.host if request.client else "unknown")
    if refused:
        raise HTTPException(status_code=429, detail=refused)
    gate = _gate()
    if gate is not None:
        verdict = gate.check(req.question)
        if not verdict.allowed:  # blocked or undecided: the main model is not called
            return AskResponse(answer=OUT_OF_SCOPE_ANSWER, stop_reason="out_of_scope", steps=[],
                               tokens=verdict.tokens, latency_ms=0, run_id="")
    llm, tools = _agent()
    with _lock:
        result = ask(req.question, llm=llm, tools=tools)
    return AskResponse(answer=result.answer, stop_reason=result.stop_reason,
                       steps=[Step(**s) for s in result.steps], tokens=result.tokens_in + result.tokens_out,
                       latency_ms=result.latency_ms, run_id=result.run_id, flagged=result.flagged)
