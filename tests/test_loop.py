"""The loop's limits, tested with a scripted fake model (no network, no API key)."""
import json

import pytest

from agentkit.llm import LLMResponse, ToolCall
from agentkit.loop import run_agent
from agentkit.trace import Tracer
from process_copilot.tools import connect, make_tools


class ScriptedLLM:
    """Plays back a fixed list of responses and records what it was sent."""
    model = "scripted"

    def __init__(self, responses):
        self.responses = list(responses)
        self.seen = []

    def chat(self, messages, tools=None):
        self.seen.append([dict(m) for m in messages])
        resp = self.responses.pop(0)
        if resp.tool_calls:
            resp.raw_message = {"role": "assistant", "content": None, "tool_calls": [
                {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.arguments}}
                for c in resp.tool_calls]}
        return resp


def call(name, **args):
    return LLMResponse(content=None, tool_calls=[ToolCall(f"c{name}{len(args)}", name, json.dumps(args))])


@pytest.fixture(scope="module")
def tools(db_path):
    con = connect(db_path)
    yield make_tools(con)
    con.close()


def test_tool_then_answer(tools, tmp_path):
    llm = ScriptedLLM([call("run_sql", query="SELECT count(*) AS n FROM cases"),
                       LLMResponse(content="There are 6 order lines [r1].")])
    out = run_agent("How many lines?", llm=llm, tools=tools, system_prompt="sys", tracer=Tracer(tmp_path / "t.duckdb"))
    assert out.stop_reason == "answered" and out.answer == "There are 6 order lines [r1]."
    assert out.steps[0]["result_id"] == "r1"
    tool_msg = llm.seen[1][-1]
    assert tool_msg["role"] == "tool" and '"rows": [[6]]' in tool_msg["content"]


def test_tool_error_is_fed_back_to_the_model(tools):
    llm = ScriptedLLM([call("run_sql", query="DELETE FROM cases"), LLMResponse(content="I can only read data.")])
    out = run_agent("Delete everything", llm=llm, tools=tools, system_prompt="sys")
    assert out.steps[0]["ok"] is False
    assert "read-only" in llm.seen[1][-1]["content"]
    assert out.stop_reason == "answered"


def test_repeated_identical_call_stops_the_run(tools):
    same = call("get_case_timeline", case_id="4507000229_00010")
    llm = ScriptedLLM([same, call("get_case_timeline", case_id="4507000229_00010")])
    out = run_agent("loop", llm=llm, tools=tools, system_prompt="sys")
    assert out.stop_reason == "loop_detected" and out.answer is None


def test_max_steps(tools):
    llm = ScriptedLLM([call("run_sql", query=f"SELECT {i}") for i in range(5)])
    out = run_agent("never ends", llm=llm, tools=tools, system_prompt="sys", max_steps=3)
    assert out.stop_reason == "max_steps" and len(out.steps) == 3


def test_run_is_traced(tools, tmp_path):
    import duckdb
    path = tmp_path / "traces.duckdb"
    llm = ScriptedLLM([call("run_sql", query="SELECT 1"), LLMResponse(content="done")])
    run_agent("q", llm=llm, tools=tools, system_prompt="sys", tracer=Tracer(path))
    con = duckdb.connect(str(path), read_only=True)
    assert con.execute("SELECT stop_reason, n_steps FROM runs").fetchall() == [("answered", 1)]
    kinds = [r[0] for r in con.execute("SELECT kind FROM steps ORDER BY step, kind").fetchall()]
    assert kinds == ["llm", "tool", "llm"]


def test_token_budget_stops_an_expensive_run(tools):
    expensive = call("run_sql", query="SELECT count(*) FROM cases")
    expensive.tokens_in = 40_000
    llm = ScriptedLLM([expensive, LLMResponse(content="never reached")])
    out = run_agent("How many lines?", llm=llm, tools=tools, system_prompt="sys")
    assert out.stop_reason == "token_budget" and out.answer is None and out.steps == []
