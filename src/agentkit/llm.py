"""One client for any OpenAI-compatible chat API (Groq, Gemini, OpenAI, Ollama). Switching provider is config."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from dotenv import load_dotenv

PROVIDERS = {
    # name: (base_url, env var holding the key)
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY"),
    "openai": ("https://api.openai.com/v1", "OPENAI_API_KEY"),
    "anthropic": ("https://api.anthropic.com/v1", "ANTHROPIC_API_KEY"),  # OpenAI-compatible endpoint; not yet run
    "ollama": ("http://localhost:11434/v1", None),
}
RETRY_STATUS = {429, 500, 502, 503, 504}


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # raw JSON text, validated by the tool layer


@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    raw_message: dict[str, Any] = field(default_factory=dict)  # appended back to the conversation as-is
    cost_usd: float = 0.0  # list-price cost when the provider reports it (the claude CLI does)


class LLMClient:
    def __init__(self, provider: str | None = None, model: str | None = None,
                 timeout_s: float = 60, max_retries: int = 8):
        load_dotenv()
        self.provider = provider or os.getenv("LLM_PROVIDER", "groq")
        self.model = model or os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
        base_url, key_var = PROVIDERS[self.provider]
        key = os.getenv(key_var) if key_var else "ollama"
        if not key:
            raise RuntimeError(f"Set {key_var} in .env to use provider '{self.provider}'.")
        self.http = httpx.Client(base_url=base_url, timeout=timeout_s, headers={"Authorization": f"Bearer {key}"})
        self.max_retries = max_retries
        self.throttled_ms = 0  # time spent waiting on rate limits, kept apart from model latency

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> LLMResponse:
        body: dict[str, Any] = {"model": self.model, "messages": messages, "temperature": 0}
        if tools:
            body["tools"] = tools
        started = time.perf_counter()
        for attempt in range(self.max_retries + 1):
            resp = self.http.post("/chat/completions", json=body)
            # provider hiccups and rate limits: back off and retry (tool errors are NOT retried here)
            if resp.status_code == 429 and resp.headers.get("x-should-retry") == "false":
                resp.raise_for_status()  # a daily quota, not a burst: fail now instead of waiting per call
            if resp.status_code in RETRY_STATUS and attempt < self.max_retries:
                wait = min(float(resp.headers.get("retry-after", 2 ** attempt)), 60)
                time.sleep(wait)
                self.throttled_ms += round(wait * 1000)
                continue
            resp.raise_for_status()
            break
        data = resp.json()
        message = data["choices"][0]["message"]
        usage = data.get("usage") or {}
        calls = [ToolCall(c["id"], c["function"]["name"], c["function"].get("arguments") or "{}")
                 for c in message.get("tool_calls") or []]
        clean = {k: v for k, v in message.items() if k in ("role", "content", "tool_calls")}
        return LLMResponse(
            content=message.get("content"), tool_calls=calls,
            tokens_in=usage.get("prompt_tokens", 0), tokens_out=usage.get("completion_tokens", 0),
            latency_ms=round((time.perf_counter() - started) * 1000), raw_message=clean,
        )
