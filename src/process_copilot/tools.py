"""The P2 agent's tools: read-only SQL over the warehouse, and one order line's timeline."""
from __future__ import annotations

import re
import threading
from pathlib import Path
from typing import Any

import duckdb
from pydantic import BaseModel, Field

from agentkit.tools import Tool

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "data" / "p2p.duckdb"

MAX_ROWS = 200          # rows a query may return (C2 cost: results go into the model's context)
ROWS_TO_MODEL = 30      # rows shown to the model; the full result is kept in the result store
QUERY_TIMEOUT_S = 10    # C1 latency
TIMELINE_MAX_EVENTS = 40

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|merge|create|drop|alter|truncate|attach|detach|copy|export|import|"
    r"install|load|pragma|set|reset|call|checkpoint|vacuum|use)\b",
    re.IGNORECASE,
)
CASE_ID = re.compile(r"^\d{10}_\d{5}$")


def connect(db_path: Path = DEFAULT_DB) -> duckdb.DuckDBPyConnection:
    """Read-only by construction: no writes, no files, no extensions, settings locked (C4)."""
    con = duckdb.connect(str(db_path), read_only=True)
    con.execute("SET enable_external_access = false")
    con.execute("SET lock_configuration = true")
    return con


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"--[^\n]*", " ", sql)
    return re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)


def _strip_strings(sql: str) -> str:
    return re.sub(r"'(?:[^']|'')*'", "''", sql)


def check_query(sql: str) -> str | None:
    """Return an error message the model can act on, or None if the query is allowed."""
    body = _strip_comments(sql).strip().rstrip(";").strip()
    if not body:
        return "Empty query."
    code = _strip_strings(body)
    if ";" in code:
        return "Only one statement per call. Remove the extra ';'."
    if not re.match(r"^(select|with)\b", code, re.IGNORECASE):
        return "Only SELECT queries (optionally starting with WITH) are allowed: the warehouse is read-only."
    bad = FORBIDDEN.search(code)
    if bad:
        return f"'{bad.group(0).upper()}' is not allowed: the warehouse is read-only."
    return None


def _run_with_timeout(con: duckdb.DuckDBPyConnection, sql: str) -> tuple[list[str], list[tuple]]:
    """Fetch at most MAX_ROWS + 1 rows (the +1 tells us the result was cut), within QUERY_TIMEOUT_S."""
    timer = threading.Timer(QUERY_TIMEOUT_S, con.interrupt)
    timer.start()
    try:
        cur = con.execute(sql)
        return [d[0] for d in cur.description], cur.fetchmany(MAX_ROWS + 1)
    except duckdb.InterruptException as exc:
        raise TimeoutError(f"Query took longer than {QUERY_TIMEOUT_S}s. Aggregate more or filter first.") from exc
    finally:
        timer.cancel()


def _jsonable(rows: list[tuple]) -> list[list[Any]]:
    return [[v.isoformat(sep=" ") if hasattr(v, "isoformat") else v for v in row] for row in rows]


class RunSqlArgs(BaseModel):
    query: str = Field(..., max_length=4000, description="One DuckDB SELECT statement over the warehouse tables.")


class TimelineArgs(BaseModel):
    case_id: str = Field(..., description="Order line id, e.g. 4507000229_00010 (PO number + '_' + 5-digit item).")


def make_tools(con: duckdb.DuckDBPyConnection) -> dict[str, Tool]:
    def run_sql(query: str) -> dict[str, Any]:
        error = check_query(query)
        if error:
            return {"ok": False, "error": error}
        body = _strip_comments(query).strip().rstrip(";")
        columns, rows = _run_with_timeout(con, body)
        truncated = len(rows) > MAX_ROWS
        rows = _jsonable(rows[:MAX_ROWS])
        return {
            "ok": True, "columns": columns, "row_count": len(rows), "truncated": truncated,
            "rows": rows[:ROWS_TO_MODEL],
            "note": (f"Showing {min(len(rows), ROWS_TO_MODEL)} of {len(rows)} rows"
                     + (f"; result capped at {MAX_ROWS}, aggregate instead." if truncated else ".")),
            "_full": {"query": body, "columns": columns, "rows": rows},
        }

    def get_case_timeline(case_id: str) -> dict[str, Any]:
        if not CASE_ID.match(case_id):
            return {"ok": False, "error": "case_id must look like 4507000229_00010 "
                                          "(10-digit PO number, '_', 5-digit item)."}
        case = con.execute("""
            SELECT case_id, document_type, item_category, vendor, spend_area, value_eur,
                   strftime(start_ts, '%Y-%m-%d') AS start, strftime(end_ts, '%Y-%m-%d') AS "end",
                   throughput_days, n_events
            FROM cases WHERE case_id = ?""", [case_id]).fetchone()
        if case is None:
            return {"ok": False, "error": f"No order line {case_id}. Use run_sql to search cases by po or vendor."}
        case_cols = ["case_id", "document_type", "item_category", "vendor", "spend_area", "value_eur",
                     "start", "end", "throughput_days", "n_events"]
        events = con.execute("""
            SELECT e.seq, e.event_id, e.activity, strftime(e.ts, '%Y-%m-%d %H:%M') AS ts,
                   round(date_diff('second', lag(e.ts) OVER (ORDER BY e.seq), e.ts) / 86400.0, 1) AS wait_days,
                   e.user_id, e.n_identical, e.ts_status
            FROM events e WHERE e.case_id = ? AND e.is_canonical ORDER BY e.seq""", [case_id]).fetchall()
        event_cols = ["seq", "event_id", "activity", "ts", "wait_days", "user_id", "n_identical", "ts_status"]
        cycles = con.execute("""
            SELECT cycle_no, strftime(start_ts, '%Y-%m-%d'), strftime(end_ts, '%Y-%m-%d'), days, is_closed
            FROM cycles WHERE case_id = ? ORDER BY cycle_no""", [case_id]).fetchall()
        shown = events
        omitted = None
        if len(events) > TIMELINE_MAX_EVENTS:  # long contracts: first and last steps plus a summary
            half = TIMELINE_MAX_EVENTS // 2
            shown = events[:half] + events[-half:]
            middle = events[half:-half]
            counts: dict[str, int] = {}
            for e in middle:
                counts[e[2]] = counts.get(e[2], 0) + 1
            omitted = {"n_events": len(middle), "activities": counts}
        result = {
            "ok": True,
            "case": dict(zip(case_cols, case, strict=True)),
            "event_columns": event_cols,
            "events": [list(e) for e in shown],
            "omitted_middle": omitted,
            "cycles": [{"cycle_no": c[0], "start": c[1], "end": c[2], "days": c[3], "closed": c[4]}
                       for c in cycles],
            "note": "Canonical events only (identical copies collapsed, n_identical shows how many). "
                    "wait_days = days since the previous step. Supplier events carry a date, not a real time.",
        }
        result["_full"] = {**result, "events": [list(e) for e in events]}
        return result

    return {
        "run_sql": Tool(
            name="run_sql",
            description=(
                "Run one read-only DuckDB SELECT over the warehouse. Use it for counts, rankings, "
                "medians and anything across many order lines. Tables: events, cases, cycles, dq_report. "
                f"Returns at most {MAX_ROWS} rows; aggregate in SQL instead of fetching raw rows."
            ),
            args_model=RunSqlArgs, fn=run_sql,
        ),
        "get_case_timeline": Tool(
            name="get_case_timeline",
            description=(
                "Get one order line's ordered steps with waiting time between them, its attributes and its "
                "payment cycles. Use it to explain why a specific line was slow; cite seq/event_id as evidence."
            ),
            args_model=TimelineArgs, fn=get_case_timeline,
        ),
    }
