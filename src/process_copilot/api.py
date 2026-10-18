"""HTTP API for the Process Copilot agent.

Run: uvicorn process_copilot.api:app --port 8000   → docs at http://localhost:8000/docs
"""
from __future__ import annotations

import threading
from functools import lru_cache

from fastapi import FastAPI
from pydantic import BaseModel, Field

from process_copilot.agent import ask, build_agent

app = FastAPI(title="Process Copilot", description="Ask questions about the purchase-to-pay process.")
_lock = threading.Lock()  # one DuckDB connection and one agent run at a time (enough for a demo)


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


@lru_cache(maxsize=1)
def _agent():
    return build_agent()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(req: AskRequest) -> AskResponse:
    llm, tools = _agent()
    with _lock:
        result = ask(req.question, llm=llm, tools=tools)
    return AskResponse(answer=result.answer, stop_reason=result.stop_reason,
                       steps=[Step(**s) for s in result.steps], tokens=result.tokens_in + result.tokens_out,
                       latency_ms=result.latency_ms, run_id=result.run_id)
