from app.norms import load_norms, norms_block


def test_norms_load_and_ids_unique():
    norms = load_norms()
    ids = [p["id"] for p in norms["passages"]]
    assert len(ids) == len(set(ids)) >= 10
    assert any(i.startswith("cmrec2022-16:") for i in ids)
    assert any(i.startswith("echr:") for i in ids)
    assert any(i.startswith("cets189:") for i in ids)


def test_norms_block_renders_citation_ids():
    block = norms_block()
    assert "[cmrec2022-16:def]" in block


def test_tier_label_valid_and_invalid():
    import pytest
    from app.norms import tier_label
    assert tier_label(1) == "ordinary political expression"
    assert tier_label(4) == "high-severity incitement/dehumanisation risk"
    with pytest.raises(ValueError):
        tier_label(99)


def test_system_passages_excluded_from_default_block():
    from app.norms import norms_block, passages_by_tag
    block = norms_block()
    system = passages_by_tag("system")
    assert system
    for p in system:
        assert p["id"] not in block
