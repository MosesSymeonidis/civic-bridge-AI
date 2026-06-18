from ingest.build_registry import COE_STATES, cyprus_entry, build


def test_cyprus_entry_is_verified_and_complete():
    cy = cyprus_entry()
    assert cy["verified"] is True
    assert cy["police_cybercrime"]["name"]
    assert any("116111" in h["phone"].replace(" ", "") for h in cy["helplines"])


def test_build_covers_all_states():
    registry = build(equinet_html=None)
    assert len(registry) == len(COE_STATES) == 46
    assert registry["Cyprus"]["verified"] is True
    assert registry["France"]["verified"] is False
