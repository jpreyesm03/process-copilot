"""The HTTP contract of /ask, with a scripted model and the fixture warehouse."""
import pytest
from fastapi.testclient import TestClient

from agentkit.limits import UsageLimiter
from agentkit.llm import LLMResponse
from process_copilot import api
from process_copilot.agent import BLOCKED_ANSWER
from process_copilot.tools import connect, make_tools
from tests.test_loop import ScriptedLLM, call


@pytest.fixture
def client(db_path, monkeypatch, tmp_path):
    llm = ScriptedLLM([call("run_sql", query="SELECT count(*) FROM cases"), LLMResponse(content="6 lines [r1].")])
    tools = make_tools(connect(db_path))
    monkeypatch.setattr(api, "_agent", lambda: (llm, tools))
    monkeypatch.setattr("process_copilot.agent.TRACES", tmp_path / "traces.duckdb")
    monkeypatch.setattr(api, "limiter", UsageLimiter())
    return TestClient(api.app)


def test_ask_returns_answer_and_trajectory(client):
    r = client.post("/ask", json={"question": "How many order lines are there?"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "6 lines [r1]." and body["stop_reason"] == "answered"
    assert body["steps"][0]["tool"] == "run_sql" and body["steps"][0]["result_id"] == "r1"


def test_question_is_validated(client):
    assert client.post("/ask", json={"question": ""}).status_code == 422
    assert client.get("/health").json() == {"status": "ok"}


BURGER = "Our vendor charges 100 EUR for 85 paint cans plus 30 lids. If a lid costs 0.50 EUR, what does one can cost?"


def test_arithmetic_on_user_numbers_is_withheld(db_path, monkeypatch, tmp_path):
    # the model takes the bait: 85x + 30 * 0.5 = 100 -> x = 1.00; no tool ever returned 1.00
    llm = ScriptedLLM([LLMResponse(content="One can costs 1.00 EUR (100 - 30 x 0.50 = 85, / 85).")])
    monkeypatch.setattr(api, "_agent", lambda: (llm, make_tools(connect(db_path))))
    monkeypatch.setattr("process_copilot.agent.TRACES", tmp_path / "traces.duckdb")
    body = TestClient(api.app).post("/ask", json={"question": BURGER}).json()
    assert body["answer"] == BLOCKED_ANSWER and "1.00" in body["blocked"]


def test_usage_limit_returns_429(client, monkeypatch):
    monkeypatch.setattr(api, "limiter", UsageLimiter(per_client_per_hour=1))
    assert client.post("/ask", json={"question": "How many order lines are there?"}).status_code == 200
    r = client.post("/ask", json={"question": "How many order lines are there?"})
    assert r.status_code == 429 and "per hour" in r.json()["detail"]
