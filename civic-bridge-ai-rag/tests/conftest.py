import pytest

from app import stats


@pytest.fixture(autouse=True)
def _isolated_stats_db(tmp_path, monkeypatch):
    """Keep test runs from writing analysis events into the real demo DB."""
    monkeypatch.setattr(stats, "DB_PATH", tmp_path / "stats.db")
