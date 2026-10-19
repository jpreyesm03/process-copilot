"""Build the DuckDB warehouse from the BPI 2019 events CSV.

Tables:
  events(event_id, case_id, seq, activity, ts, ts_original, ts_status, resource, user_id, value_eur,
         n_identical, is_canonical)
  cases(case_id, po, item, item_category, item_type, vendor, company, spend_area, sub_spend_area,
        document_type, gr_based_inv_verif, goods_receipt_flag, value_eur, n_events, n_bad_dates,
        start_ts, end_ts, throughput_days)
  cycles(case_id, cycle_no, start_ts, end_ts, days, n_events, is_closed, closing_event_id)
  dq_report(check_name, n, note)

Decisions applied (see DECISIONS.md):
  D1  out-of-range dates are repaired when exactly one year fits the line, otherwise flagged
  D2  the case is the PO line item, as delivered
  D3  case value = value at "Create Purchase Order Item"
  D4  each payment (Clear Invoice) closes a cycle; cycles are measured separately
  D5  "NONE" in user/resource becomes NULL
  D6  timestamps parsed as UTC datetimes
  D7  identical rows are kept; one canonical copy per group is used for sequences

Usage: python -m process_copilot.build_db [--csv PATH] [--db PATH]
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV = ROOT / "data" / "processed" / "bpi2019_events.csv.gz"
DEFAULT_DB = ROOT / "data" / "p2p.duckdb"

# D1: the log was extracted in 2019; anything outside this window is a data-entry error
VALID_FROM, VALID_TO = "2017-01-01", "2020-01-01"
# D1: a repaired date must fall within the line's own timeline, give or take this many days
REPAIR_WINDOW_DAYS = 60


def build(csv_path: Path, db_path: Path) -> None:
    db_path.unlink(missing_ok=True)
    con = duckdb.connect(str(db_path))
    t0 = time.time()

    # raw: everything as text, plus the file row number (the file is chronological per case)
    con.execute("""
        CREATE TEMP TABLE raw AS
        SELECT row_number() OVER () AS file_row, *
        FROM read_csv(?, all_varchar = true)
    """, [str(csv_path)])

    # step 1: types and hidden nulls (D5, D6); the file row becomes a stable event_id
    con.execute(f"""
        CREATE TEMP TABLE parsed AS
        SELECT
            file_row                                                        AS event_id,
            case_id,
            activity,
            strptime(left(timestamp, 19), '%Y-%m-%dT%H:%M:%S')              AS ts_original,
            ts_original >= TIMESTAMP '{VALID_FROM}'
                AND ts_original < TIMESTAMP '{VALID_TO}'                    AS in_range,
            nullif(resource, 'NONE')                                        AS resource,
            nullif("user", 'NONE')                                          AS user_id,
            TRY_CAST(cum_net_worth_eur AS DOUBLE)                           AS value_eur
        FROM raw
    """)

    # step 2 (D1): for each out-of-range date, try the same day and minute in 2017-2019
    con.execute(f"""
        CREATE TEMP TABLE ts_repair AS
        WITH line_window AS (
            SELECT case_id, min(ts_original) AS first_ts, max(ts_original) AS last_ts
            FROM parsed WHERE in_range GROUP BY case_id
        ),
        candidates AS (
            SELECT b.event_id, b.case_id, b.activity,
                   TRY_CAST(y.year::VARCHAR || strftime(b.ts_original, '-%m-%d %H:%M:%S') AS TIMESTAMP)
                       AS candidate_ts
            FROM parsed b, (SELECT unnest([2017, 2018, 2019]) AS year) y
            WHERE NOT b.in_range
        ),
        scored AS (
            SELECT c.event_id, c.candidate_ts,
                   EXISTS (SELECT 1 FROM parsed v
                           WHERE v.in_range AND v.case_id = c.case_id
                             AND v.activity = c.activity AND v.ts_original = c.candidate_ts) AS has_twin,
                   -- another event on the same line at that exact minute (e.g. invoice + debit memo)
                   EXISTS (SELECT 1 FROM parsed v
                           WHERE v.in_range AND v.case_id = c.case_id
                             AND v.ts_original = c.candidate_ts)                          AS has_companion,
                   c.candidate_ts BETWEEN w.first_ts - INTERVAL {REPAIR_WINDOW_DAYS} DAY
                                      AND w.last_ts + INTERVAL {REPAIR_WINDOW_DAYS} DAY   AS plausible
            FROM candidates c LEFT JOIN line_window w USING (case_id)
            WHERE c.candidate_ts IS NOT NULL
        ),
        decided AS (
            SELECT event_id,
                   bool_or(has_twin)                                        AS is_duplicate,
                   count(*) FILTER (WHERE plausible)                        AS n_plausible,
                   count(*) FILTER (WHERE plausible AND has_companion)      AS n_with_companion,
                   any_value(candidate_ts) FILTER (WHERE plausible)                    AS only_plausible,
                   any_value(candidate_ts) FILTER (WHERE plausible AND has_companion)  AS only_companion
            FROM scored GROUP BY event_id
        )
        SELECT event_id,
               CASE WHEN is_duplicate           THEN 'duplicate'
                    WHEN n_plausible = 1        THEN 'repaired'
                    WHEN n_with_companion = 1   THEN 'repaired'      -- tie broken by a same-minute event
                    ELSE 'unresolved' END                                AS ts_status,
               CASE WHEN is_duplicate           THEN NULL
                    WHEN n_plausible = 1        THEN only_plausible
                    WHEN n_with_companion = 1   THEN only_companion END  AS ts_repaired
        FROM decided
    """)

    # step 3 (D7): keep identical rows, count them, and mark one canonical copy per group;
    # sequences and cycles only use canonical rows with a trustworthy date
    con.execute("""
        CREATE TABLE events AS
        WITH dated AS (
            SELECT p.*,
                   -- an out-of-range date with no candidate (e.g. Feb 29 → no leap year in 2017-19)
                   -- has no repair row: it must still count as unresolved, never as ok
                   coalesce(r.ts_status, CASE WHEN p.in_range THEN 'ok' ELSE 'unresolved' END) AS ts_status,
                   CASE WHEN r.ts_status IS NULL THEN p.ts_original ELSE r.ts_repaired END AS ts
            FROM parsed p LEFT JOIN ts_repair r USING (event_id)
        ),
        copies AS (
            SELECT *,
                   count(*)     OVER same_row                       AS n_identical,
                   row_number() OVER (same_row ORDER BY event_id)   AS copy_no
            FROM dated
            WINDOW same_row AS (PARTITION BY case_id, activity, ts_original, resource, user_id, value_eur)
        ),
        flagged AS (
            SELECT *, ts_status IN ('ok', 'repaired') AND copy_no = 1 AS is_canonical FROM copies
        )
        SELECT event_id, case_id,
               CASE WHEN is_canonical THEN
                   row_number() OVER (PARTITION BY case_id, is_canonical ORDER BY ts, event_id)
               END AS seq,
               activity, ts, ts_original, ts_status, resource, user_id, value_eur,
               n_identical, is_canonical
        FROM flagged
        ORDER BY case_id, ts, event_id
    """)

    con.execute("""
        CREATE TABLE cases AS
        WITH attrs AS (
            SELECT case_id,
                   any_value(case_purchasing_document)       AS po,
                   any_value(case_item)                      AS item,
                   any_value(case_item_category)             AS item_category,
                   any_value(case_item_type)                 AS item_type,
                   any_value(case_vendor)                    AS vendor,
                   any_value(case_company)                   AS company,
                   any_value(case_spend_area_text)           AS spend_area,
                   any_value(case_sub_spend_area_text)       AS sub_spend_area,
                   any_value(case_document_type)             AS document_type,
                   any_value(case_gr_based_inv_verif) = 'true' AS gr_based_inv_verif,
                   any_value(case_goods_receipt) = 'true'    AS goods_receipt_flag
            FROM raw GROUP BY case_id
        ),
        stats AS (
            SELECT case_id,
                   count(*)                                                       AS n_events,
                   count(*) FILTER (WHERE ts_status <> 'ok')                       AS n_bad_dates,
                   min(ts) FILTER (WHERE ts_status IN ('ok', 'repaired'))          AS start_ts,
                   max(ts) FILTER (WHERE ts_status IN ('ok', 'repaired'))          AS end_ts,
                   -- D3: the ordered amount
                   arg_min(value_eur, event_id)
                       FILTER (WHERE activity = 'Create Purchase Order Item')     AS value_eur
            FROM events GROUP BY case_id
        )
        SELECT a.*, s.value_eur, s.n_events, s.n_bad_dates, s.start_ts, s.end_ts,
               round(date_diff('second', s.start_ts, s.end_ts) / 86400.0, 2) AS throughput_days
        FROM attrs a JOIN stats s USING (case_id)
        ORDER BY case_id
    """)

    # D4: split each line into payment cycles. An event's cycle = 1 + number of payments (Clear Invoice)
    # strictly before it, so each payment closes the cycle it belongs to. Canonical events only (D7).
    con.execute("""
        CREATE TABLE cycles AS
        WITH numbered AS (
            SELECT case_id, event_id, seq, activity, ts,
                   1 + coalesce(sum(CASE WHEN activity = 'Clear Invoice' THEN 1 ELSE 0 END) OVER (
                           PARTITION BY case_id ORDER BY seq
                           ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0) AS cycle_no
            FROM events
            WHERE is_canonical
        )
        SELECT case_id,
               cycle_no,
               min(ts)                                                         AS start_ts,
               max(ts)                                                         AS end_ts,
               round(date_diff('second', min(ts), max(ts)) / 86400.0, 2)       AS days,
               count(*)                                                        AS n_events,
               bool_or(activity = 'Clear Invoice')                             AS is_closed,
               max(event_id) FILTER (WHERE activity = 'Clear Invoice')         AS closing_event_id
        FROM numbered
        GROUP BY case_id, cycle_no
        ORDER BY case_id, cycle_no
    """)

    # one row per gap between consecutive trusted steps, with the keys of its peer groups (same vendor; same
    # item category and value band), so a wait can be compared with the same gap elsewhere
    con.execute("""
        CREATE TABLE waits AS
        WITH steps AS (
            SELECT case_id, seq, activity, ts,
                   lag(activity) OVER w AS from_activity, lag(seq) OVER w AS from_seq, lag(ts) OVER w AS from_ts
            FROM events
            WHERE is_canonical AND seq IS NOT NULL AND ts_status IN ('ok', 'repaired')
            WINDOW w AS (PARTITION BY case_id ORDER BY seq)
        ),
        bands AS (SELECT case_id, vendor, item_category, ntile(5) OVER (ORDER BY value_eur, case_id) AS value_band
                  FROM cases)
        SELECT s.case_id, s.from_seq, s.seq AS to_seq, s.from_activity, s.activity AS to_activity,
               round(date_diff('second', s.from_ts, s.ts) / 86400.0, 1) AS days,
               b.vendor, b.item_category, b.value_band
        FROM steps s JOIN bands b USING (case_id)
        WHERE s.from_activity IS NOT NULL
        ORDER BY s.case_id, s.seq
    """)

    # data-quality report: every cleaning rule is counted, nothing is silently dropped
    con.execute("""
        CREATE TABLE dq_report AS
        SELECT 'events_total' AS check_name, count(*) AS n, 'rows in the source CSV' AS note FROM events
        UNION ALL SELECT 'cases_total', count(*), 'PO line items (D2)' FROM cases
        UNION ALL SELECT 'dates_repaired', count(*) FILTER (WHERE ts_status = 'repaired'),
                         'year typo fixed: one plausible year, or a same-minute companion (D1)' FROM events
        UNION ALL SELECT 'dates_duplicate', count(*) FILTER (WHERE ts_status = 'duplicate'),
                         'bad-date copy of an existing event (D1)' FROM events
        UNION ALL SELECT 'dates_unresolved', count(*) FILTER (WHERE ts_status = 'unresolved'),
                         'kept, excluded from sequences and durations (D1)' FROM events
        UNION ALL SELECT 'cases_with_bad_dates', count(*) FILTER (WHERE n_bad_dates > 0),
                         'lines with at least one out-of-range date' FROM cases
        UNION ALL SELECT 'rows_identical_extra', count(*) FILTER (WHERE n_identical > 1 AND NOT is_canonical
                                                                   AND ts_status IN ('ok', 'repaired')),
                         'identical copies kept but not canonical (D7)' FROM events
        UNION ALL SELECT 'events_canonical', count(*) FILTER (WHERE is_canonical),
                         'rows used for sequences and cycles' FROM events
        UNION ALL SELECT 'cycles_total', count(*), 'payment cycles across all lines (D4)' FROM cycles
        UNION ALL SELECT 'cycles_open', count(*) FILTER (WHERE NOT is_closed),
                         'cycles with no closing payment yet (D4)' FROM cycles
        UNION ALL SELECT 'events_null_value', count(*) FILTER (WHERE value_eur IS NULL),
                         'cumulative net worth missing or unparsable' FROM events
        UNION ALL SELECT 'cases_value_changes', count(*),
                         'value differs across events (D3 uses Create PO Item)'
                  FROM (SELECT case_id FROM events GROUP BY 1 HAVING count(DISTINCT value_eur) > 1)
    """)
    con.close()
    print(f"built {db_path.name} in {time.time() - t0:.1f}s")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    a = ap.parse_args()
    build(a.csv, a.db)
    con = duckdb.connect(str(a.db), read_only=True)
    for row in con.execute("SELECT * FROM dq_report").fetchall():
        print(f"  {row[0]:<24} {row[1]:>10,}  {row[2]}")


if __name__ == "__main__":
    main()
