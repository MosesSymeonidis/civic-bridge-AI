from unittest.mock import MagicMock, patch

from ingest.enrich_cases import best_match, hudoc_query_url, THEME_VOCAB


def test_hudoc_query_url_contains_case_name():
    url = hudoc_query_url("Leroy v France")
    assert "Leroy" in url and "hudoc.echr.coe.int" in url


def test_best_match_picks_exact_docname():
    results = [
        {"docname": "CASE OF LEROY v. FRANCE", "appno": "36109/03",
         "kpdate": "2008-10-02T00:00:00", "conclusion": "No violation of Art. 10"},
        {"docname": "CASE OF OTHER v. FRANCE", "appno": "1/01",
         "kpdate": "2000-01-01T00:00:00", "conclusion": "x"},
    ]
    match, status = best_match("Leroy v France", results)
    assert match["appno"] == "36109/03"
    assert status == "matched"


def test_best_match_flags_ambiguous():
    match, status = best_match("Leroy v France", [])
    assert match is None and status == "no_match"


def test_theme_vocab_enforcement():
    """Out-of-vocabulary LLM themes must be dropped (set to empty string)."""
    from ingest.enrich_cases import _apply_theme_mapping

    cases = [
        {"name": "Leroy v France", "theme": ""},
        {"name": "Garaudy v France", "theme": ""},
    ]
    # LLM returns one valid theme and one invalid/out-of-vocab theme
    llm_mapping = {
        "Leroy v France": "Violence and terrorism",      # valid
        "Garaudy v France": "Holocaust Denial",           # not in THEME_VOCAB
    }
    _apply_theme_mapping(cases, llm_mapping)

    assert cases[0]["theme"] == "Violence and terrorism"
    assert cases[1]["theme"] == ""  # invalid theme must be dropped
