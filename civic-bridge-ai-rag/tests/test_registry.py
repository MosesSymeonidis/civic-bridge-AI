import pytest

from app.registry import authorities, cases_by_theme, helplines


def test_authorities_cyprus_verified():
    cy = authorities("Cyprus")
    assert cy["verified"] is True
    assert cy["police_cybercrime"]["name"]


def test_authorities_unknown_country():
    with pytest.raises(KeyError):
        authorities("Atlantis")


def test_cases_by_theme_limit_and_fields():
    cases = cases_by_theme(["Ethnic Hatred", "Violence"], limit=3)
    assert 0 < len(cases) <= 3
    assert all({"name", "theme", "conclusion", "url"} <= set(c) for c in cases)
    assert all(c["url"].startswith("https://hudoc.echr.coe.int/") for c in cases)


def test_helplines_cyprus():
    lines = helplines("Cyprus")
    assert any("116" in h["phone"].replace(" ", "") for h in lines)


def test_authorities_mutation_does_not_corrupt_cache():
    cy1 = authorities("Cyprus")
    cy1["verified"] = False
    cy1["police_cybercrime"]["name"] = "MUTATED"
    cy2 = authorities("Cyprus")
    assert cy2["verified"] is True
    assert cy2["police_cybercrime"]["name"] != "MUTATED"


def test_cases_mutation_does_not_corrupt_cache():
    first = cases_by_theme(["Ethnic Hatred"], limit=1)
    first[0]["conclusion"] = "MUTATED"
    fresh = cases_by_theme(["Ethnic Hatred"], limit=1)
    assert fresh[0]["conclusion"] != "MUTATED"
