import json
from pathlib import Path

GOLDEN = Path(__file__).parent / "golden_set.jsonl"


def test_golden_set_is_valid():
    entries = [json.loads(l) for l in GOLDEN.read_text().splitlines() if l.strip()]
    assert len(entries) >= 10
    from app.codebook import load_codebook
    known = set(load_codebook()["barriers"])
    ids = [e["id"] for e in entries]
    assert len(ids) == len(set(ids))
    for e in entries:
        assert 1 <= e["tier_min"] <= e["tier_max"] <= 4
        assert set(e["barriers"]) <= known, e["id"]
