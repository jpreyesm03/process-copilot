"""Process Copilot demo: purchase-to-pay metrics, an AI analyst over the data, a line explorer and the eval results.

Run locally:  uv run streamlit run app/streamlit_app.py
On Streamlit Community Cloud the warehouse is built from the event log at start-up (about 10-30 s, then cached).
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import uuid
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agentkit.limits import UsageLimiter  # noqa: E402
from process_copilot.build_db import build  # noqa: E402
from process_copilot.tools import connect, make_tools  # noqa: E402

DB = Path(os.getenv("P2P_DB", ROOT / "data" / "p2p.duckdb"))
CSV_CANDIDATES = [ROOT / "data_public" / "bpi2019_events.csv.gz", ROOT / "data" / "processed" / "bpi2019_events.csv.gz"]
RECORDED = json.loads((ROOT / "app" / "recorded_answers.json").read_text())
PER_DAY = int(os.getenv("LIMIT_PER_DAY", "25"))  # Groq free tier: ~200k tokens/day at ~7k tokens per question
PER_HOUR = int(os.getenv("LIMIT_PER_CLIENT_HOUR", "8"))

st.set_page_config(page_title="Process Copilot", page_icon="📦", layout="wide")


def _secrets_to_env() -> None:
    """Streamlit Cloud keeps keys in st.secrets; the agent reads them from the environment."""
    try:  # every top-level secret: provider keys (e.g. GROQ_API_KEY), LLM_*, TOPIC_*, LIMIT_*
        for key, value in st.secrets.items():
            if isinstance(value, str | int | float) and key not in os.environ:
                os.environ[key] = str(value)
    except Exception:  # no secrets file locally: .env is used instead
        pass


@st.cache_resource(show_spinner="Building the warehouse from the event log (first start only)...")
def warehouse() -> Path:
    if not DB.exists():
        csv = next((p for p in CSV_CANDIDATES if p.exists()), None)
        if csv is None:
            st.error("No event log found. Expected data_public/bpi2019_events.csv.gz.")
            st.stop()
        DB.parent.mkdir(parents=True, exist_ok=True)
        build(csv, DB)
    return DB


@st.cache_resource
def con() -> duckdb.DuckDBPyConnection:
    return connect(warehouse())


@st.cache_resource
def agent():
    """The model client plus tools on the shared connection (DuckDB allows one configured connection per file)."""
    _secrets_to_env()
    from agentkit.llm import LLMClient

    return LLMClient(), make_tools(con())


@st.cache_resource
def shared() -> tuple[threading.Lock, UsageLimiter]:
    return threading.Lock(), UsageLimiter(per_client_per_hour=PER_HOUR, per_day=PER_DAY)


@st.cache_resource
def gate():
    """Topic gate (D14): a small model with its own quota screens every question before the main model."""
    _secrets_to_env()
    from process_copilot.agent import topic_gate

    return topic_gate(), UsageLimiter(per_client_per_hour=30, per_day=500)


def q(sql: str, params: list | None = None) -> pd.DataFrame:
    lock, _ = shared()
    with lock:  # one DuckDB connection shared by all sessions
        return con().execute(sql, params or []).df()


def eur(x: float) -> str:
    return f"€{x / 1e6:,.2f}M" if x >= 1e6 else f"€{x:,.0f}"


# ---------------------------------------------------------------- pages
def overview() -> None:
    st.title("Where purchase-to-pay loses time and money")
    st.caption("1.6M SAP events · 251,734 order lines · a coatings company · "
               "orders created in 2018 (data ends 18 Jan 2019)")
    s = q("SELECT * FROM m_summary")
    get = dict(zip(s["metric"], zip(s["value"], s["eur"], strict=True), strict=True))
    c1, c2, c3, c4 = st.columns(4)
    n, e = get["paid before any goods receipt (3-way match)"]
    c1.metric("Paid before any goods arrived", eur(e), f"{n:,.0f} order lines", delta_color="off")
    n, e = get["open longer than the vendor usually takes"]
    c2.metric("Open longer than the vendor usually takes", eur(e), f"{n:,.0f} invoices", delta_color="off")
    n, e = get["open invoices"]
    c3.metric("All open invoices", eur(e), f"{n:,.0f} lines", delta_color="off")
    top10 = s.loc[s["metric"].str.startswith("share of lines"), "value"].iloc[0]
    c4.metric("Lines on the 10 most common paths", f"{top10:.0f}%", "7,433 different paths", delta_color="off")
    st.info("There are no due dates or payment terms in this data, so nothing is called overdue: an invoice is "
            "flagged when it has been open longer than 90% of the same vendor's paid invoices took.")

    left, right = st.columns(2)
    with left:
        st.subheader("Where the waiting time goes")
        b = q("""SELECT from_activity || ' → ' || to_activity AS step, pct_of_all_waiting AS pct, median_days
                 FROM m_bottlenecks ORDER BY total_wait_days DESC LIMIT 8""")
        st.bar_chart(b, x="step", y="pct", horizontal=True, y_label="% of all waiting (paid first cycles)", x_label="")
        st.caption("Invoice receipt → payment is partly payment terms by design; blocks and rework are the waste.")
    with right:
        st.subheader("What rework costs")
        r = q("""SELECT activity, extra_days_same_category_and_value AS extra_days, pct_of_lines
                 FROM m_rework WHERE extra_days_same_category_and_value > 0 ORDER BY extra_days DESC""")
        st.bar_chart(r, x="activity", y="extra_days", horizontal=True, y_label="extra days to first payment",
                     x_label="")
        st.caption("Compared with lines of the same item category and value band (a correlation, not proof).")

    st.subheader("Invoices to chase first")
    st.dataframe(q("""SELECT case_id AS order_line, vendor, round(value_eur) AS value_eur, invoice_recorded, days_open,
                             vendor_p90_days AS vendor_usually_pays_within_days
                      FROM m_open_invoices WHERE status LIKE 'open longer%' ORDER BY value_eur DESC LIMIT 15"""),
                 hide_index=True, width="stretch")


def ask_page() -> None:
    st.title("Ask the data")
    st.caption(f"An AI analyst that answers with SQL and order-line timelines over the warehouse, cites its evidence "
               f"and marks any number it cannot trace to the data. Only questions about this purchase-to-pay data are "
               f"answered (a topic check runs first). Live model: gpt-oss-120b (Groq free tier, about "
               f"{PER_DAY} questions a day for everyone). When the live model is unavailable, recorded answers "
               f"from the evaluated configuration are shown for the sample questions.")
    if "sid" not in st.session_state:
        st.session_state.sid = uuid.uuid4().hex
    samples = [r["question"] for r in RECORDED]
    pick = st.selectbox("Try a sample question", ["(write your own below)", *samples])
    question = st.chat_input("Ask about orders, vendors, invoices, delays...")
    if not question and pick != "(write your own below)":
        question = pick
    if not question:
        return
    st.chat_message("user").write(question)
    answers = st.session_state.setdefault("answers", {})
    if question not in answers:  # Streamlit reruns the page on every click: answer each question once per visitor
        answers[question] = _answer(question)
    kind, text, steps, footer = answers[question]
    with st.chat_message("assistant"):
        if kind == "warning":
            st.warning(text)
            return
        if kind == "recorded":  # footer = (why the live model was not used, where the answer was recorded)
            st.warning(footer[0])
            footer = footer[1]
        st.markdown(text)
        if steps is not None:
            _show_steps(steps, footer)


def _answer(question: str) -> tuple[str, str, list | None, object]:
    """('live' | 'recorded' | 'blocked' | 'warning', text, steps, footer)."""
    from process_copilot.agent import OUT_OF_SCOPE_ANSWER, ask

    lock, limiter = shared()
    recorded = next((r for r in RECORDED if r["question"] == question), None)
    error = None
    if recorded is None:  # sample questions skip the topic check: they are known to be in scope
        try:
            topic, topic_limiter = gate()
            error = topic_limiter.check(st.session_state.sid)
            if not error:
                verdict = topic.check(question)
                if verdict.allowed is not True:
                    note = "" if verdict.allowed is False else " (The topic check is unavailable right now.)"
                    return "blocked", OUT_OF_SCOPE_ANSWER + note, None, ""
        except Exception as exc:  # missing key or provider down: never show a stack trace to a visitor
            error = f"The live model is unavailable right now ({type(exc).__name__})."
    error = error or limiter.check(st.session_state.sid)
    if not error:
        try:
            llm, tools = agent()
            with lock, st.spinner("Querying the warehouse..."):
                result = ask(question, llm=llm, tools=tools)
            if result.answer:
                tokens = result.tokens_in + result.tokens_out
                return "live", result.answer, result.steps, f"{tokens:,} tokens · {result.latency_ms / 1000:.1f} s"
            error = f"No answer within the step and token limits ({result.stop_reason})."
        except Exception as exc:  # quota, missing key, network: fall back to recorded answers
            error = f"The live model is unavailable right now ({type(exc).__name__})."
    if recorded:
        note = f"{error} Showing a recorded answer from the evaluated configuration ({recorded['model']})."
        return "recorded", recorded["answer"], recorded["steps"], (note, f"recorded in eval run {recorded['run']}")
    return "warning", f"{error} Pick one of the sample questions to see a recorded answer.", None, ""


def _show_steps(steps: list[dict], footer: str) -> None:
    with st.expander(f"How I got this ({len(steps)} tool calls)"):
        for i, s in enumerate(steps, 1):
            args = s["args"]
            try:
                parsed = json.loads(args) if isinstance(args, str) else args
                body = parsed.get("query") or json.dumps(parsed)
            except (json.JSONDecodeError, AttributeError):
                body = str(args)
            st.markdown(f"**{i}. `{s['tool']}`**")
            st.code(body, language="sql" if s["tool"] == "run_sql" else "json")
        st.caption(footer)


def explorer() -> None:
    st.title("Why was this order line slow?")
    st.caption("Every wait between two steps, compared with the same step at the same vendor and at similar lines "
               "(same item category and value band). No AI here: this is the data the analyst reads.")
    examples = ["4507000365_00010", "4507004456_00010", "4507008595_00010", "4507000905_00050"]
    case_id = st.selectbox("Order line", examples, accept_new_options=True)
    lock, _ = shared()
    with lock:
        out = make_tools(con())["get_case_timeline"].fn(case_id=case_id.strip())
    if not out.get("ok"):
        st.error(out.get("error"))
        return
    c = out["case"]
    cols = st.columns(4)
    cols[0].metric("Vendor", c["vendor"])
    cols[1].metric("Value", eur(c["value_eur"] or 0))
    cols[2].metric("Order to last step", f"{c['throughput_days']:.0f} days")
    fp = out.get("first_payment_vs_peers")
    if fp:
        peers = f"vendor median {fp['vendor_median']:.0f} d · {fp['vendor_pctile']:.0f}th pct"
        cols[3].metric("Order to first payment", f"{fp['days']:.0f} days", peers, delta_color="off")
    waits = pd.DataFrame(out["waits"])
    waits["step"] = waits["from"] + " → " + waits["to"]
    st.subheader("Waits between steps")
    st.bar_chart(waits, x="step", y="days", horizontal=True, x_label="", y_label="days")
    show = [col for col in ["step", "days", "vendor_median", "vendor_pctile", "similar_median", "similar_pctile",
                            "n_vendor", "n_similar"] if col in waits]
    st.dataframe(waits[show], hide_index=True, width="stretch")
    st.caption("pctile = % of peers that waited less: about 50 is typical, 90+ is unusually slow. "
               "Benchmarks are computed for the three longest waits.")
    with st.expander("All events"):
        st.dataframe(pd.DataFrame(out["events"], columns=out["event_columns"]), hide_index=True)


def quality() -> None:
    st.title("How we know it works")
    text = (ROOT / "evals" / "EVALS.md").read_text()
    text = re.sub(r"\[([^\]]+)\]\((?:runs/)[^)]*\)", r"\1", text)  # run links point inside the repo
    st.markdown(text)


START = os.getenv("P2P_START_PAGE", "overview")  # lets headless tests open another page first
pg = st.navigation([
    st.Page(overview, title="Overview", icon="📊", default=START == "overview"),
    st.Page(ask_page, title="Ask the data", icon="💬", default=START == "ask"),
    st.Page(explorer, title="Line explorer", icon="🔎"),
    st.Page(quality, title="How we know it works", icon="✅"),
])
st.sidebar.caption("Data: van Dongen, B. (2019) BPI Challenge 2019, 4TU.ResearchData, CC BY 4.0. Built by JP Reyes.")
pg.run()
