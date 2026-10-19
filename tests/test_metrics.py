"""Process metrics on the fixture warehouse: the parts add up and each table follows its definition."""

import duckdb
import pytest


@pytest.fixture(scope="module")
def con(db_path):
    con = duckdb.connect(str(db_path), read_only=True)
    yield con
    con.close()


def one(con, sql):
    return con.execute(sql).fetchone()


def test_every_line_is_in_exactly_one_variant(con):
    assert one(con, "SELECT sum(n_lines) FROM m_variants") == one(con, "SELECT count(*) FROM cases")
    assert one(con, "SELECT max(cum_pct) FROM m_variants")[0] == pytest.approx(100)


def test_bottleneck_shares_add_up_to_all_waiting(con):
    assert one(con, "SELECT sum(pct_of_all_waiting) FROM m_bottlenecks")[0] == pytest.approx(100, abs=0.5)


def test_open_invoices_are_received_but_never_paid(con):
    paid_or_no_goods = one(con, """
        SELECT count(*) FROM m_open_invoices o
        WHERE EXISTS (SELECT 1 FROM events e WHERE e.case_id = o.case_id AND e.activity = 'Clear Invoice')
           OR NOT EXISTS (SELECT 1 FROM events e WHERE e.case_id = o.case_id AND e.activity = 'Record Goods Receipt')
    """)[0]
    assert paid_or_no_goods == 0
    # the fixture's unpaid line F never got a goods receipt, so it is not an open invoice
    assert one(con, "SELECT count(*) FROM m_open_invoices WHERE case_id = '4507000288_00010'")[0] == 0


def test_summary_has_the_headline_numbers(con):
    metrics = [r[0] for r in con.execute("SELECT metric FROM m_summary").fetchall()]
    assert metrics[:3] == ["open invoices", "open longer than the vendor usually takes",
                           "paid before any goods receipt (3-way match)"]
    assert any(m.startswith("largest bottleneck: ") for m in metrics)
