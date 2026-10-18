"""The HTTP contract of /ask, with a scripted model and the fixture warehouse."""
import pytest
from fastapi.testclient import TestClient

from agentkit.llm import LLMResponse
from process_copilot import api
from process_copilot.tools import connect, make_tools
from tests.test_loop import ScriptedLLM, call


@pytest.fixture
def client(db_path, monkeypatch, tmp_path):
    llm = ScriptedLLM([call("run_sql", query="SELECT count(*) FROM cases"), LLMResponse(content="6 lines [r1].")])
    tools = make_tools(connect(db_path))
    monkeypatch.setattr(api, "_agent", lambda: (llm, tools))
    monkeypatch.setattr("process_copilot.agent.TRACES", tmp_path / "traces.duckdb")
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
