from app import stats


def test_record_and_aggregate():
    stats.record(tier=3, barriers=["rigid_opposition", "distrust"],
                 themes=["Ethnic Hatred"], country="Cyprus", role="teacher",
                 age_band="14-17")
    stats.record(tier=1, barriers=[], themes=[], country="Cyprus",
                 role="student", age_band="10-13")
    agg = stats.aggregate()
    assert agg["analyses_total"] == 2
    assert agg["analyses_last_7_days"] == 2
    assert agg["by_tier"]["3"] == 1 and agg["by_tier"]["1"] == 1
    assert ("rigid_opposition", 1) in agg["top_barriers"]
    assert agg["by_role"] == {"teacher": 1, "student": 1}
    assert agg["by_country"] == {"Cyprus": 2}
    assert "no usernames" in agg["privacy_note"].lower() or "identifiers" in agg["privacy_note"]


def test_aggregate_empty_is_valid():
    agg = stats.aggregate()
    assert agg["analyses_total"] == 0
    assert agg["by_tier"] == {"1": 0, "2": 0, "3": 0, "4": 0}
    assert agg["top_barriers"] == []


def test_record_never_raises(monkeypatch):
    monkeypatch.setattr(stats, "DB_PATH", "/nonexistent/dir/stats.db")
    stats.record(tier=2, barriers=[], themes=[])  # must not raise
