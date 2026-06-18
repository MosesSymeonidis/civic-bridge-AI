from app.codebook import load_codebook, promoters_for, activities_for, codebook_block


def test_codebook_has_seven_barriers_with_required_fields():
    cb = load_codebook()
    assert len(cb["barriers"]) == 7
    for b in cb["barriers"].values():
        assert b["definition"] and b["markers"] and b["promoters"]
        assert len(b["examples"]) >= 2
        assert set(b["activities"]) == {"6-9", "10-13", "14-17", "18+"}


def test_promoters_for_is_deterministic_lookup():
    promoters = promoters_for("rigid_opposition")
    assert "superordinate_identity" in promoters


def test_unknown_barrier_raises():
    import pytest
    with pytest.raises(KeyError):
        promoters_for("nonsense")


def test_codebook_block_fits_in_context():
    assert 2000 < len(codebook_block()) < 30000
