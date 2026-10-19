"""Grading logic of the eval runner (no model calls)."""

import json

from process_copilot.evaluate import auto_grade, report

UNPAID = {"id": "amb_01", "type": "ambiguous", "numbers": [4302, 16.3], "assume": True, "tol": 0.02}
RESULTS = {"r1": {"rows": [[4302, 16301234.5]]}}


def test_auto_grade_passes_grounded_answer_with_keys():
    g = auto_grade(UNPAID, "Assuming due lines: 4,302 lines, €16.3M [r1].", ["run_sql"], RESULTS, "answered")
    assert g["ok"], g["checks"]


def test_auto_grade_fails_wrong_number_and_invented_one():
    g = auto_grade(UNPAID, "27,570 lines, €102.6M [r1].", ["run_sql"], RESULTS, "answered")
    assert not g["checks"]["number 4302"] and not g["checks"]["all numbers grounded"]


def test_mentions_accept_alternatives_and_tool_is_required():
    q = {"id": "case_04", "type": "case", "mentions": ["Change Price|price change"], "tool": "get_case_timeline"}
    g = auto_grade(q, "The price change came late.", ["run_sql"], {}, "answered")
    assert g["checks"]["mentions 'Change Price|price change'"] and not g["checks"]["used get_case_timeline"]


def test_report_needs_every_run_to_pass_and_judge_to_agree(tmp_path):
    def row(qid, repeat, ok, judge):
        return {"id": qid, "type": "t", "repeat": repeat, "needs_judge": judge, "latency_ms": 1000, "tokens": 900,
                "auto": {"ok": ok, "checks": {"x": ok}, "ungrounded": [], "n_numbers": 1, "n_derived": 0}}

    rows = [row("a", 1, True, False), row("a", 2, True, False), row("b", 1, True, True), row("b", 2, False, True)]
    (tmp_path / "answers.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    (tmp_path / "meta.json").write_text(json.dumps({"model": "m", "provider": "p", "prompt_version": "v1",
                                                     "repeats": 2}))
    (tmp_path / "judgments.json").write_text(json.dumps({"b#1": {"pass": True}, "b#2": {"pass": True}}))
    text = report(tmp_path)
    assert "**1/2 (50%)**" in text  # a passes both runs; b fails run 2 on an auto check
    assert "3/4 (75%)" in text
