"""Extract a few real order lines from the full BPI 2019 CSV into a small test fixture.

Each line is chosen to exercise one modelling decision (see tests/test_build_db.py).
usage: python scripts/make_fixture.py
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "processed" / "bpi2019_events.csv.gz"
TARGET = ROOT / "tests" / "fixtures" / "sample_events.csv.gz"

LINES = [
    "4507000229_00010",  # A: plain line, one payment
    "4507004931_00010",  # B: 1948 dates, one repaired and one duplicate
    "2000000097_00001",  # C: repair by same-minute companion, four payment cycles
    "4507003966_00010",  # D: unresolvable dates, including Feb 29
    "4508062734_00001",  # E: three identical rows
    "4507000288_00010",  # F: consignment, never paid
]


def main() -> None:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    ids = ", ".join(f"'{c}'" for c in LINES)
    duckdb.execute(f"""
        COPY (
            SELECT * FROM read_csv('{SOURCE}', all_varchar = true)
            WHERE case_id IN ({ids})
        ) TO '{TARGET}' (HEADER, COMPRESSION gzip)
    """)
    n = duckdb.execute(f"SELECT count(*) FROM read_csv('{TARGET}')").fetchone()[0]
    print(f"wrote {n} events from {len(LINES)} lines to {TARGET.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
