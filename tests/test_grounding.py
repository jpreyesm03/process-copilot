"""Grounding: which numbers in an answer came from a tool result."""

import pytest

from agentkit.grounding import check, extract_numbers

RESULTS = {
    "r1": {"columns": ["lines", "eur"], "rows": [[4302, 16301234.5], [27570, 102.6e6]]},
    "r2": {"rows": [["Remove Payment Block", 40.0], ["vendor median", 6.3], ["share", 0.653]]},
}


def status(answer: str) -> dict[str, str]:
    return {n.text: n.status for n in check(answer, RESULTS)}


@pytest.mark.parametrize("text", ["4,302", "4 302", "4 302", "4 302"])
def test_thousands_separators(text):
    assert [n.value for n in extract_numbers(f"{text} lines")] == [4302]


def test_units_and_ids_are_handled():
    nums = extract_numbers("€16.3M and 102.6 million for 4507000229_00010 [r1], seq 6→7 on 2018-03-13, top 5")
    assert [n.value for n in nums] == [16.3e6, 102.6e6]


def test_grounded_rounded_rescaled_and_percent():
    s = status("4,302 lines, €16.3M, 27 570 lines (€102.6 million); 40.0 days vs 6.3; 65.3% of lines")
    assert set(s.values()) == {"grounded"}


def test_derived_difference_is_not_invented():
    assert status("+33.7 days over the median") == {"+33.7": "derived"}


def test_invented_numbers_are_flagged():
    assert status("It took 812 days, 99.1% of lines") == {"812": "ungrounded", "99.1%": "ungrounded"}


def test_broken_formatting_is_caught():
    # the U+202F glitch seen in phase 4: "27,570" written as "275 70"
    assert "ungrounded" in status("275 70 lines").values()


def test_small_number_with_a_unit_is_kept():
    # time_01 baseline: "10 days" was dropped as a "small count", failing a correct answer
    assert [n.value for n in extract_numbers("Median: 10 days, top 5 vendors")] == [10]


def test_dates_times_ordinals_and_code_are_not_quantities():
    text = (
        "Record Invoice Receipt 2018‑04‑26 15:32 [seq 5 → seq 6], "
        "the median (50th percentile) via `PERCENTILE_CONT(0.5)` for 4507000365‑00010, Vendor ID 0278 【r2】"
    )
    assert extract_numbers(text) == []


def test_numbers_from_the_question_count_as_grounded():
    found = check("Among vendors with ≥ 1,000 lines: 65.3%", RESULTS, question="at least 1,000 order lines")
    assert {n.status for n in found} == {"grounded"}


def test_written_dates_and_spaced_ids_are_not_quantities():
    assert extract_numbers("created on 5 Feb 2018, recorded 30 May 2018 for 4507000365 _00010") == []


def test_ratio_of_two_results_is_derived():
    # 40.0 / 6.3 = 6.35 and 6.3 / 40.0 = 0.16
    assert status("40.0 vs 6.3 days: 6.35 times, 0.16") == {
        "40.0": "grounded", "6.3": "grounded", "6.35": "derived", "0.16": "derived"}


def test_column_total_is_grounded_but_a_wrong_sum_is_not():
    results = {"r1": {"columns": ["type", "n"], "rows": [["A", 248755], ["B", 1539], ["C", 1440]]}}
    found = {n.text: n.status for n in check("Total 251,734 lines; earlier I said 250,734", results)}
    assert found == {"251,734": "grounded", "250,734": "ungrounded"}
