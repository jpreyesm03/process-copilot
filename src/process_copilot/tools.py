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
BENCHMARKED_WAITS = 3  # the longest gaps of a line get peer medians and percentiles

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


def _peer_stats(con: duckdb.DuckDBPyConnection, sql_from: str, value: float, keys: dict[str, Any]) -> dict[str, Any]:
    """Median and percentile of `value` among peers with the same vendor, and with the same category + value band."""
    row = con.execute(f"""
        SELECT count(*) FILTER (WHERE vendor = $vendor),
               round(median(days) FILTER (WHERE vendor = $vendor), 1),
               round(100 * avg((days < $value)::int) FILTER (WHERE vendor = $vendor)),
               count(*) FILTER (WHERE item_category = $category AND value_band = $band),
               round(median(days) FILTER (WHERE item_category = $category AND value_band = $band), 1),
               round(100 * avg((days < $value)::int) FILTER (WHERE item_category = $category AND value_band = $band))
        {sql_from}""", {**keys, "value": value}).fetchone()
    names = ["n_vendor", "vendor_median", "vendor_pctile", "n_similar", "similar_median", "similar_pctile"]
    return dict(zip(names, row, strict=True))


def _waits_vs_peers(con: duckdb.DuckDBPyConnection, case_id: str) -> list[dict[str, Any]]:
    rows = con.execute("""
        SELECT from_seq, to_seq, from_activity, to_activity, days, vendor, item_category, value_band
        FROM waits WHERE case_id = ? ORDER BY to_seq""", [case_id]).fetchall()
    out = [{"from_seq": r[0], "to_seq": r[1], "from": r[2], "to": r[3], "days": r[4]} for r in rows]
    longest = sorted(range(len(rows)), key=lambda i: rows[i][4] or 0, reverse=True)[:BENCHMARKED_WAITS]
    for i in longest:
        r = rows[i]
        keys = {"vendor": r[5], "category": r[6], "band": r[7], "from": r[2], "to": r[3]}
        out[i] |= _peer_stats(con, "FROM waits WHERE from_activity = $from AND to_activity = $to", r[4], keys)
    if len(out) > TIMELINE_MAX_EVENTS:  # long contracts: keep the benchmarked waits, then the first ones
        keep = set(longest) | set(range(TIMELINE_MAX_EVENTS - len(longest)))
        out = [w for i, w in enumerate(out) if i in keep]
    return out


def _first_payment_vs_peers(con: duckdb.DuckDBPyConnection, case_id: str) -> dict[str, Any] | None:
    """Order to first payment (closed cycle 1) of this line vs the same peers. None if not paid yet."""
    row = con.execute("""
        SELECT y.days, w.vendor, w.item_category, w.value_band
        FROM cycles y JOIN (SELECT DISTINCT case_id, vendor, item_category, value_band FROM waits) w USING (case_id)
        WHERE y.case_id = ? AND y.cycle_no = 1 AND y.is_closed""", [case_id]).fetchone()
    if row is None:
        return None
    keys = {"vendor": row[1], "category": row[2], "band": row[3]}
    peers = """FROM (SELECT y.days, w.vendor, w.item_category, w.value_band FROM cycles y
                     JOIN (SELECT DISTINCT case_id, vendor, item_category, value_band FROM waits) w USING (case_id)
                     WHERE y.cycle_no = 1 AND y.is_closed)"""
    return {"days": row[0], **_peer_stats(con, peers, row[0], keys)}


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
                   e.user_id, e.n_identical, e.ts_status
            FROM events e WHERE e.case_id = ? AND e.is_canonical ORDER BY e.seq""", [case_id]).fetchall()
        event_cols = ["seq", "event_id", "activity", "ts", "user_id", "n_identical", "ts_status"]
        waits = _waits_vs_peers(con, case_id)
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
            "waits": waits,
            "first_payment_vs_peers": _first_payment_vs_peers(con, case_id),
            "note": "Canonical events only (identical copies collapsed, n_identical shows how many). "
                    "Each wait is the gap between two named steps (from -> to), not a property of either step. "
                    f"The {BENCHMARKED_WAITS} longest waits are compared with the same gap at the same vendor and "
                    "at similar lines (same item_category and value band, 5 equal-size bands by value): "
                    "pctile = % of peers that waited less (50 typical, 90+ unusually slow); "
                    "treat n under 30 as weak evidence. Supplier events carry a date, not a real time.",
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
                "Get one order line's ordered steps, the waits between them (the longest ones compared with "
                "the same vendor and similar lines), its first payment time vs peers, its attributes and its "
                "payment cycles. Use it to explain why a specific line was slow; cite seq/event_id as evidence."
            ),
            args_model=TimelineArgs, fn=get_case_timeline,
        ),
    }
