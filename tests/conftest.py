from pathlib import Path

import pytest

from process_copilot.build_db import build

FIXTURE = Path(__file__).parent / "fixtures" / "sample_events.csv.gz"


@pytest.fixture(scope="session")
def db_path(tmp_path_factory) -> Path:
    """The warehouse built once from the 6-line fixture, shared by all tests."""
    path = tmp_path_factory.mktemp("db") / "test.duckdb"
    build(FIXTURE, path)
    return path
