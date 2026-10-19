"""Process metrics (Phase 6): tables built once from the warehouse, read by the agent, the app and the tests.

m_bottlenecks   where waiting time goes, per step pair (paid first cycles)
m_variants      the paths lines take through the process
m_rework        rework events and their extra days, compared within the same item category and value band
m_conformance   rule violations with the money involved
m_open_invoices unpaid invoices: how long open, and whether longer than this vendor's paid invoices took
m_summary       one row per headline number, for the overview page

No due dates or payment terms exist in the data (D9), so nothing here is called overdue: "open longer than this
vendor usually takes to pay" is measured against the vendor's own paid invoices.
"""

from __future__ import annotations

import duckdb

MIN_PEERS = 30  # below this many peers a comparison is too weak to report
DATA_END_QUANTILE = 0.9999  # the extract ends where 99.99% of trusted events lie (drops a few stray far dates)
REWORK = ("Change Price", "Change Quantity", "Remove Payment Block", "Cancel Invoice Receipt", "Cancel Goods Receipt",
          "Change Approval for Purchase Order")


def build_metrics(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(f"""
        CREATE OR REPLACE TABLE m_data_end AS
        SELECT CAST(quantile_disc(ts, {DATA_END_QUANTILE}) AS DATE) AS data_end
        FROM events WHERE ts_status IN ('ok', 'repaired')
    """)

    # waits inside first cycles that ended in a payment: comparable across lines (D4)
    con.execute("""
        CREATE OR REPLACE TABLE m_bottlenecks AS
        WITH paid AS (
            SELECT y.case_id, e.seq AS last_seq FROM cycles y JOIN events e ON e.event_id = y.closing_event_id
            WHERE y.cycle_no = 1 AND y.is_closed),
        w AS (SELECT w.* FROM waits w JOIN paid p USING (case_id) WHERE w.to_seq <= p.last_seq)
        SELECT from_activity, to_activity, count(*) AS n_waits,
               round(median(days), 1) AS median_days,
               round(quantile_cont(days, 0.9), 1) AS p90_days,
               round(sum(days)) AS total_wait_days,
               round(100 * sum(days) / sum(sum(days)) OVER (), 1) AS pct_of_all_waiting
        FROM w GROUP BY 1, 2 ORDER BY total_wait_days DESC
    """)

    # a variant = the ordered activities of a line, consecutive repeats collapsed
    con.execute("""
        CREATE OR REPLACE TABLE m_variants AS
        WITH s AS (
            SELECT case_id, seq, activity, lag(activity) OVER (PARTITION BY case_id ORDER BY seq) AS prev
            FROM events WHERE is_canonical AND seq IS NOT NULL),
        p AS (SELECT case_id, string_agg(activity, ' > ' ORDER BY seq) AS path
              FROM s WHERE prev IS DISTINCT FROM activity GROUP BY 1),
        v AS (
            SELECT p.path, count(*) AS n_lines, median(y.days) FILTER (WHERE y.is_closed) AS median_first_cycle_days
            FROM p LEFT JOIN cycles y ON y.case_id = p.case_id AND y.cycle_no = 1 GROUP BY 1)
        SELECT row_number() OVER (ORDER BY n_lines DESC, path) AS variant_rank, path, n_lines,
               round(100.0 * n_lines / sum(n_lines) OVER (), 2) AS pct_lines,
               round(100.0 * sum(n_lines) OVER (ORDER BY n_lines DESC, path) / sum(n_lines) OVER (), 2) AS cum_pct,
               round(median_first_cycle_days, 1) AS median_first_cycle_days
        FROM v ORDER BY variant_rank
    """)

    # rework cost: in each item category x value band, median first-cycle days with vs without the event;
    # the extra days are the line-weighted average of those within-group gaps (groups with >= MIN_PEERS each side)
    rework = ", ".join(f"'{a}'" for a in REWORK)
    con.execute(f"""
        CREATE OR REPLACE TABLE m_rework AS
        WITH lines AS (
            SELECT y.case_id, y.days, w.item_category, w.value_band
            FROM cycles y JOIN (SELECT DISTINCT case_id, item_category, value_band FROM waits) w USING (case_id)
            WHERE y.cycle_no = 1 AND y.is_closed),
        flags AS (SELECT DISTINCT case_id, activity FROM events WHERE is_canonical AND activity IN ({rework})),
        acts AS (SELECT unnest([{rework}]) AS activity),
        grid AS (
            SELECT a.activity, l.*, f.case_id IS NOT NULL AS has_it
            FROM acts a CROSS JOIN lines l LEFT JOIN flags f ON f.case_id = l.case_id AND f.activity = a.activity),
        groups AS (
            SELECT activity, item_category, value_band,
                   count(*) FILTER (WHERE has_it) AS n_with, count(*) FILTER (WHERE NOT has_it) AS n_without,
                   median(days) FILTER (WHERE has_it) AS med_with, median(days) FILTER (WHERE NOT has_it) AS med_without
            FROM grid GROUP BY 1, 2, 3)
        SELECT g.activity,
               (SELECT count(DISTINCT case_id) FROM flags f WHERE f.activity = g.activity) AS lines_with_event,
               round(100.0 * (SELECT count(DISTINCT case_id) FROM flags f WHERE f.activity = g.activity)
                     / (SELECT count(*) FROM cases), 1) AS pct_of_lines,
               round(sum((med_with - med_without) * n_with) FILTER (WHERE n_with >= {MIN_PEERS}
                     AND n_without >= {MIN_PEERS}) / sum(n_with) FILTER (WHERE n_with >= {MIN_PEERS}
                     AND n_without >= {MIN_PEERS}), 1) AS extra_days_same_category_and_value,
               sum(n_with) FILTER (WHERE n_with >= {MIN_PEERS} AND n_without >= {MIN_PEERS}) AS paid_lines_compared
        FROM groups g GROUP BY g.activity ORDER BY lines_with_event DESC
    """)

    # conformance rules: each row = rule x item category, with the lines it applies to and the ones breaking it
    con.execute("""
        CREATE OR REPLACE TABLE m_conformance AS
        WITH f AS (
            SELECT e.case_id,
                   min(ts) FILTER (WHERE activity = 'Record Goods Receipt') AS gr,
                   min(ts) FILTER (WHERE activity = 'Record Invoice Receipt') AS ir,
                   min(ts) FILTER (WHERE activity = 'Clear Invoice') AS paid
            FROM events e WHERE is_canonical AND ts_status IN ('ok', 'repaired') GROUP BY 1),
        x AS (SELECT f.*, c.item_category, c.value_eur FROM f JOIN cases c USING (case_id))
        SELECT 'paid before any goods receipt' AS rule, item_category,
               count(*) FILTER (WHERE paid IS NOT NULL) AS lines_checked,
               count(*) FILTER (WHERE paid < gr OR (paid IS NOT NULL AND gr IS NULL)) AS violations,
               round(sum(value_eur) FILTER (WHERE paid < gr OR (paid IS NOT NULL AND gr IS NULL)), 2) AS eur
        FROM x WHERE item_category LIKE '3-way%' GROUP BY 1, 2
        UNION ALL
        SELECT 'invoice recorded before goods receipt', item_category,
               count(*) FILTER (WHERE ir IS NOT NULL AND gr IS NOT NULL),
               count(*) FILTER (WHERE ir < gr),
               round(sum(value_eur) FILTER (WHERE ir < gr), 2)
        FROM x WHERE item_category = '3-way match, invoice after GR' GROUP BY 1, 2
        ORDER BY eur DESC
    """)

    # unpaid invoices (goods and invoice in, no payment, not deleted): age at the end of the data, and the
    # vendor's own p90 of receipt-to-payment days on paid lines as the yardstick (no due dates exist, D9)
    con.execute(f"""
        CREATE OR REPLACE TABLE m_open_invoices AS
        WITH f AS (
            SELECT e.case_id,
                   bool_or(activity = 'Record Goods Receipt') AS gr,
                   min(ts) FILTER (WHERE activity = 'Record Invoice Receipt') AS invoice_recorded,
                   min(ts) FILTER (WHERE activity = 'Clear Invoice') AS paid,
                   bool_or(activity = 'Delete Purchase Order Item') AS deleted
            FROM events e WHERE is_canonical AND ts_status IN ('ok', 'repaired') GROUP BY 1),
        vendor_pay AS (
            SELECT c.vendor, count(*) AS n_paid,
                   quantile_cont(date_diff('second', f.invoice_recorded, f.paid) / 86400.0, 0.9) AS p90_days
            FROM f JOIN cases c USING (case_id) WHERE f.paid >= f.invoice_recorded GROUP BY 1)
        SELECT c.case_id, c.vendor, c.item_category, c.value_eur, CAST(f.invoice_recorded AS DATE) AS invoice_recorded,
               date_diff('day', CAST(f.invoice_recorded AS DATE), d.data_end) AS days_open,
               coalesce(v.n_paid, 0) AS vendor_paid_invoices, round(v.p90_days, 1) AS vendor_p90_days,
               CASE WHEN coalesce(v.n_paid, 0) < {MIN_PEERS} THEN 'too few vendor payments to compare'
                    WHEN date_diff('day', CAST(f.invoice_recorded AS DATE), d.data_end) > v.p90_days
                    THEN 'open longer than 90% of this vendor''s paid invoices'
                    ELSE 'within this vendor''s usual payment time' END AS status
        FROM f JOIN cases c USING (case_id) CROSS JOIN m_data_end d LEFT JOIN vendor_pay v ON v.vendor = c.vendor
        WHERE f.gr AND f.invoice_recorded IS NOT NULL AND f.paid IS NULL AND NOT f.deleted
        ORDER BY c.value_eur DESC
    """)

    con.execute("""
        CREATE OR REPLACE TABLE m_summary AS
        SELECT 'open invoices' AS metric, count(*)::DOUBLE AS value, round(sum(value_eur)) AS eur,
               'goods and invoice received, not paid, not deleted' AS note FROM m_open_invoices
        UNION ALL SELECT 'open longer than the vendor usually takes', count(*), round(sum(value_eur)),
               'beyond the vendor''s p90 receipt-to-payment time on paid invoices'
               FROM m_open_invoices WHERE status LIKE 'open longer%'
        UNION ALL SELECT 'paid before any goods receipt (3-way match)', sum(violations), round(sum(eur)),
               'payment with no goods receipt recorded first' FROM m_conformance
               WHERE rule = 'paid before any goods receipt'
        UNION ALL SELECT 'share of lines on the 10 most common paths', max(cum_pct), NULL, '% of lines'
               FROM m_variants WHERE variant_rank <= 10
        UNION ALL SELECT 'largest bottleneck: ' || from_activity || ' -> ' || to_activity, pct_of_all_waiting, NULL,
               '% of all waiting in paid first cycles' FROM m_bottlenecks QUALIFY row_number() OVER (
               ORDER BY total_wait_days DESC) = 1
    """)
