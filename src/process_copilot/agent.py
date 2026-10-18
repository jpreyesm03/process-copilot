"""The Process Copilot agent: system prompt (schema, definitions, rules) + tools + loop.

Usage: python -m process_copilot.agent "Why did 4507000229_00010 take so long?"
"""
from __future__ import annotations

import sys
from pathlib import Path

from agentkit.llm import LLMClient
from agentkit.loop import AgentResult, run_agent
from agentkit.trace import Tracer
from process_copilot.tools import DEFAULT_DB, connect, make_tools

ROOT = Path(__file__).resolve().parents[2]
TRACES = ROOT / "traces" / "traces.duckdb"
PROMPT_VERSION = "v1"

SYSTEM_PROMPT = """\
You are Process Copilot, an analyst for the procurement operations team of a coatings and paints company.
You answer questions about their purchase-to-pay process using ONLY the warehouse, through your tools.

## Warehouse (DuckDB, read-only)
events: one row per event.
  event_id, case_id, seq (step number within the line; NULL for rows excluded from sequences),
  activity, ts (UTC), ts_original, ts_status (ok | repaired | duplicate | unresolved),
  resource, user_id (NULL = supplier or system), value_eur, n_identical, is_canonical
cases: one row per order line (case_id = PO number + '_' + item).
  case_id, po, item, item_category, item_type, vendor, company, spend_area, sub_spend_area,
  document_type (Standard PO | Framework order | EC Purchase order), gr_based_inv_verif, goods_receipt_flag,
  value_eur (ordered amount), n_events, n_bad_dates, start_ts, end_ts, throughput_days
cycles: one row per payment cycle; each 'Clear Invoice' (payment) closes a cycle.
  case_id, cycle_no, start_ts, end_ts, days, n_events, is_closed, closing_event_id
dq_report: check_name, n, note (data-quality counts)

## Definitions (use these, do not invent your own)
- Throughput of a line = cases.throughput_days (first to last trusted event). Framework orders and other
  recurring lines live for months by design; for "how long does the process take" prefer cycles.days and
  compare cycles with the same cycle_no (cycle 1 includes ordering, later cycles do not).
- Use events WHERE is_canonical for counting steps and sequences (identical copies are collapsed).
- item_category = the expected flow: '3-way match, invoice before GR', '3-way match, invoice after GR',
  '2-way match' (no goods receipt needed), 'Consignment' (no invoice per line, so never paid per line).
- Supplier events ('Vendor creates invoice', 'Vendor creates debit memo') carry a date, not a real time.

## Rules
1. Every number in your answer must come from a tool result in this conversation. Never estimate.
2. Cite evidence: for a line, cite seq numbers or event_ids; for aggregates, cite the result id (e.g. [r2]).
3. If the data cannot answer (e.g. payment terms, prices agreed in contracts), say so plainly.
4. Prefer one aggregated SQL query over many small ones. Keep answers short: a direct answer first,
   then 2-4 bullet points of evidence. Money in EUR, durations in days.
"""


def build_agent(db_path: Path = DEFAULT_DB):
    con = connect(db_path)
    return LLMClient(), make_tools(con)


def ask(question: str, *, llm=None, tools=None, trace_path: Path | None = None) -> AgentResult:
    if llm is None or tools is None:
        llm, tools = build_agent()
    return run_agent(question, llm=llm, tools=tools, system_prompt=SYSTEM_PROMPT,
                     tracer=Tracer(trace_path or TRACES), prompt_version=PROMPT_VERSION)


def main() -> None:
    question = " ".join(sys.argv[1:]) or "How many order lines are there per document type?"
    result = ask(question)
    for s in result.steps:
        status = "ok" if s["ok"] else f"ERROR: {s['error']}"
        print(f"  step {s['step']}: {s['tool']}({s['args'][:140]}) -> {s['result_id'] or ''} {status}")
    print(f"\n{result.answer}\n")
    print(f"[{result.stop_reason} · {len(result.steps)} tool calls · {result.tokens_in + result.tokens_out} tokens · "
          f"{result.latency_ms / 1000:.1f}s · run {result.run_id}]")


if __name__ == "__main__":
    main()
