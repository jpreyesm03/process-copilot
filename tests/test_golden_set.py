import tomllib
from collections import Counter
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).parent.parent
GOLDEN = ROOT / "evals" / "golden_set.toml"
WAREHOUSE = ROOT / "data" / "p2p.duckdb"

QUESTIONS = tomllib.loads(GOLDEN.read_text())["q"]


def test_golden_set_shape():
    dev = [q for q in QUESTIONS if q.get("split", "dev") == "dev"]
    assert len(dev) == 20 and len(QUESTIONS) == 24
    assert len({q["id"] for q in QUESTIONS}) == 24
    assert Counter(q["type"] for q in dev) == {
        "descriptive": 3, "time": 3, "cycles": 3, "case": 4, "vendors": 3, "unanswerable": 2, "ambiguous": 2,
    }
    for q in QUESTIONS:
        gradable = q.get("numbers") or q.get("mentions") or q.get("refuse") or q.get("label")
        assert gradable, f"{q['id']} has nothing to grade"


@pytest.mark.skipif(not WAREHOUSE.exists(), reason="full warehouse not built (data is not in git)")
@pytest.mark.parametrize("q", [q for q in QUESTIONS if q.get("numbers")], ids=lambda q: q["id"])
def test_keys_match_warehouse(q):
    """Every stored key must be reproducible from its SQL on the real data."""
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    first_row = con.execute(q["key_sql"]).fetchall()
    values = [v for row in first_row for v in row]
    numeric = [float(v) for v in values if isinstance(v, int | float)]
    for expected in q["numbers"]:
        assert any(abs(v - expected) <= 1e-9 + 0.001 * abs(expected) for v in numeric), (expected, numeric)
    if q["type"] == "case":  # case mentions are words the answer must use, not values in the key
        return
    for text in q.get("mentions", []):
        assert any(text in str(v) for v in values), (text, values)
