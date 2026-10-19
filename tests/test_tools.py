"""Guardrails and outputs of the agent's tools, on the fixture warehouse."""
import pytest

from agentkit.tools import ResultStore, call_tool
from process_copilot.tools import check_query, connect, make_tools


@pytest.fixture(scope="module")
def con(db_path):
    con = connect(db_path)
    yield con
    con.close()


@pytest.fixture(scope="module")
def tools(con):
    return make_tools(con)


def run(tools, name, **args):
    return call_tool(tools, name, args, ResultStore())


@pytest.mark.parametrize("sql", [
    "DELETE FROM events",
    "DROP TABLE cases",
    "SELECT 1; DROP TABLE cases",
    "COPY events TO 'out.csv'",
    "INSTALL httpfs",
    "ATTACH 'other.duckdb'",
    "SET enable_external_access = true",
    "UPDATE cases SET value_eur = 0",
])
def test_writes_and_side_effects_are_rejected(sql):
    assert check_query(sql) is not None


@pytest.mark.parametrize("sql", [
    "SELECT count(*) FROM cases",
    "WITH x AS (SELECT * FROM cases) SELECT count(*) FROM x",
    "SELECT activity FROM events WHERE activity = 'Delete Purchase Order Item'",  # keyword inside a string
    "-- comment\nSELECT user_id FROM events LIMIT 1;",
])
def test_reads_are_allowed(sql):
    assert check_query(sql) is None


def test_files_cannot_be_read_even_through_select(tools):
    out = run(tools, "run_sql", query="SELECT * FROM read_csv('/etc/passwd')")
    assert out["ok"] is False


def test_query_result(tools):
    out = run(tools, "run_sql", query="SELECT case_id, n_events FROM cases ORDER BY n_events DESC")
    assert out["ok"] and out["columns"] == ["case_id", "n_events"]
    assert out["rows"][0] == ["4507003966_00010", 75]
    assert out["result_id"] == "r1"


def test_sql_error_is_returned_to_the_model(tools):
    out = run(tools, "run_sql", query="SELECT no_such_column FROM cases")
    assert out["ok"] is False and "no_such_column" in out["error"]


def test_timeline_of_a_plain_line(tools):
    out = run(tools, "get_case_timeline", case_id="4507000229_00010")
    assert out["ok"] and out["case"]["throughput_days"] == 86.27
    activities = [e[2] for e in out["events"]]
    assert activities[0] == "Create Purchase Order Item" and activities[-1] == "Clear Invoice"
    assert len(out["cycles"]) == 1
    first = out["waits"][0]
    assert (first["from_seq"], first["to_seq"], first["from"]) == (1, 2, "Create Purchase Order Item")
    assert len(out["waits"]) == len(out["events"]) - 1


def test_longest_waits_are_benchmarked_against_peers(tools):
    out = run(tools, "get_case_timeline", case_id="4507000229_00010")
    benchmarked = [w for w in out["waits"] if "vendor_pctile" in w]
    assert len(benchmarked) == 3
    assert max(w["days"] for w in benchmarked) == max(w["days"] for w in out["waits"])
    assert out["first_payment_vs_peers"]["days"] == out["cycles"][0]["days"]


def test_long_timeline_is_truncated_with_a_summary(tools):
    out = run(tools, "get_case_timeline", case_id="4507003966_00010")
    assert len(out["events"]) == 40 and out["omitted_middle"]["n_events"] > 0


@pytest.mark.parametrize("case_id, hint", [("4507000229", "must look like"), ("9999999999_00010", "No order line")])
def test_timeline_errors_are_actionable(tools, case_id, hint):
    out = run(tools, "get_case_timeline", case_id=case_id)
    assert out["ok"] is False and hint in out["error"]


def test_bad_arguments_and_unknown_tools(tools):
    assert "Invalid arguments" in call_tool(tools, "run_sql", "{not json", ResultStore())["error"]
    assert "Unknown tool" in call_tool(tools, "delete_everything", {}, ResultStore())["error"]


def test_timeline_v1_is_kept_for_reproducible_evals(con):
    out = make_tools(con, "v1")["get_case_timeline"].fn(case_id="4507000229_00010")
    assert "wait_days" in out["event_columns"] and "waits" not in out
