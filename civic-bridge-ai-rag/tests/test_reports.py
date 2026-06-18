from app import reports


def test_create_report_returns_draft_and_persists(tmp_path, monkeypatch):
    monkeypatch.setattr(reports, "DB_PATH", tmp_path / "r.db")
    rec = reports.create_report(
        text="example post", country="Cyprus", role="teacher",
        tier=3, tier_label="potential hate speech for human review",
        rationale=[{"citation_id": "cmrec2022-16:def", "reason": "denigrates"}],
    )
    assert rec["id"] > 0
    assert "CM/Rec(2022)16" in rec["draft"]
    assert "Office for Combating Cybercrime" in rec["draft"]
    assert "human review" in rec["draft"].lower()
    assert reports.get_report(rec["id"])["country"] == "Cyprus"


def test_draft_for_unknown_country_omits_authorities(tmp_path, monkeypatch):
    monkeypatch.setattr(reports, "DB_PATH", tmp_path / "r.db")
    rec = reports.create_report(text="x", country="Atlantis", role="teacher",
                                tier=3, tier_label="t", rationale=[])
    assert "where to send" not in rec["draft"].lower()
