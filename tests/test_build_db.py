"""Build the warehouse from a 6-line fixture; check each modelling decision against hand-verified answers."""
from datetime import datetime

import duckdb
import pytest

PLAIN = "4507000229_00010"          # A
BAD_YEAR = "4507004931_00010"       # B
COMPANION = "2000000097_00001"      # C
UNRESOLVABLE = "4507003966_00010"   # D
IDENTICAL = "4508062734_00001"      # E
UNPAID = "4507000288_00010"         # F


@pytest.fixture(scope="module")
def con(db_path):
    connection = duckdb.connect(str(db_path), read_only=True)
    yield connection
    connection.close()


def one(con, sql, params=()):
    return con.execute(sql, params).fetchone()


def test_plain_line(con):
    n_events, value, days = one(
        con, "SELECT n_events, value_eur, throughput_days FROM cases WHERE case_id = ?", [PLAIN]
    )
    assert (n_events, value, days) == (8, 16027.0, 86.27)
    cycles = con.execute("SELECT is_closed FROM cycles WHERE case_id = ?", [PLAIN]).fetchall()
    assert cycles == [(True,)]


def test_bad_year_is_repaired_or_marked_duplicate(con):
    rows = dict(con.execute("""
        SELECT activity, (ts_status, ts, seq IS NULL) FROM events
        WHERE case_id = ? AND year(ts_original) = 1948
    """, [BAD_YEAR]).fetchall())
    assert rows["Vendor creates debit memo"] == ("repaired", datetime(2018, 1, 26, 22, 59), False)
    status, ts, no_seq = rows["Vendor creates invoice"]
    assert (status, ts, no_seq) == ("duplicate", None, True)


def test_companion_repair_and_cycles(con):
    status, ts = one(con, """
        SELECT ts_status, ts FROM events WHERE case_id = ? AND year(ts_original) = 2001
    """, [COMPANION])
    assert (status, ts) == ("repaired", datetime(2018, 2, 23, 22, 59))
    cycles = con.execute("SELECT cycle_no, days, is_closed FROM cycles WHERE case_id = ? ORDER BY cycle_no",
                         [COMPANION]).fetchall()
    assert len(cycles) == 4
    assert cycles[0][1:] == (45.21, True)
    assert cycles[-1][2] is False


def test_unresolvable_dates_never_count_as_ok(con):
    # 5 end-of-month supplier invoices with no unique year (incl. Feb 29, which has no 2017-19 candidate)
    assert one(con, "SELECT count(*) FROM events WHERE case_id = ? AND ts_status = 'unresolved'",
               [UNRESOLVABLE])[0] == 5
    out_of_range_ok = one(con, """
        SELECT count(*) FROM events
        WHERE ts_status = 'ok' AND (ts_original < '2017-01-01' OR ts_original >= '2020-01-01')
    """)[0]
    assert out_of_range_ok == 0


def test_identical_rows_have_one_canonical_copy(con):
    rows = con.execute("""
        SELECT n_identical, is_canonical FROM events
        WHERE case_id = ? AND activity = 'Record Service Entry Sheet'
    """, [IDENTICAL]).fetchall()
    assert sorted(rows) == [(3, False), (3, False), (3, True)]


def test_unpaid_line_has_one_open_cycle(con):
    cycles = con.execute("SELECT is_closed FROM cycles WHERE case_id = ?", [UNPAID]).fetchall()
    assert cycles == [(False,)]


def test_every_canonical_event_in_exactly_one_cycle(con):
    in_cycles = one(con, "SELECT sum(n_events) FROM cycles")[0]
    canonical = one(con, "SELECT count(*) FROM events WHERE is_canonical")[0]
    assert in_cycles == canonical


def test_none_becomes_null(con):
    assert one(con, "SELECT count(*) FROM events WHERE user_id = 'NONE' OR resource = 'NONE'")[0] == 0
