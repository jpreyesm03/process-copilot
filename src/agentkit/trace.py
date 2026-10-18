"""Record every agent run and every step to DuckDB, so failures are read from traces, not re-run and guessed."""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

import duckdb

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id VARCHAR PRIMARY KEY, question VARCHAR, model VARCHAR, prompt_version VARCHAR,
    started_at TIMESTAMP, latency_ms INTEGER, tokens_in INTEGER, tokens_out INTEGER,
    n_steps INTEGER, stop_reason VARCHAR, answer VARCHAR);
CREATE TABLE IF NOT EXISTS steps (
    run_id VARCHAR, step INTEGER, kind VARCHAR, tool_name VARCHAR, args_json VARCHAR,
    result_id VARCHAR, ok BOOLEAN, error VARCHAR, tokens_in INTEGER, tokens_out INTEGER,
    latency_ms INTEGER, content VARCHAR);
"""


class Tracer:
    def __init__(self, path: Path | str | None):
        self.path = Path(path) if path else None
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with duckdb.connect(str(self.path)) as con:
                con.execute(SCHEMA)
        self.steps: list[tuple] = []

    def new_run(self) -> str:
        self.steps = []
        return uuid.uuid4().hex[:12]

    def step(self, run_id: str, step: int, kind: str, *, tool_name=None, args=None, result_id=None, ok=None,
             error=None, tokens_in=0, tokens_out=0, latency_ms=0, content=None) -> None:
        args_json = args if isinstance(args, str) or args is None else json.dumps(args)  # model args are JSON text
        self.steps.append((run_id, step, kind, tool_name, args_json,
                           result_id, ok, error, tokens_in, tokens_out, latency_ms, content))

    def finish(self, run_id: str, question: str, model: str, prompt_version: str, started_at: datetime,
               latency_ms: int, tokens_in: int, tokens_out: int, n_steps: int, stop_reason: str,
               answer: str | None) -> None:
        if not self.path:
            return
        with duckdb.connect(str(self.path)) as con:
            con.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        [run_id, question, model, prompt_version, started_at, latency_ms, tokens_in, tokens_out,
                         n_steps, stop_reason, answer])
            if self.steps:
                con.executemany("INSERT INTO steps VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", self.steps)
