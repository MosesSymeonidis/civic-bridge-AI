import app.classify as classify
from app.classify import LLMAnalysis, BarrierFinding, CitationRef


def _fake_llm(monkeypatch, analysis: LLMAnalysis):
    monkeypatch.setattr(classify.llm, "complete",
                        lambda messages, schema=None, **kw: analysis)


def _analysis(tier=3, barrier_id="rigid_opposition"):
    return LLMAnalysis(
        tier=tier,
        rationale=[CitationRef(citation_id="cmrec2022-16:def",
                               reason="denigrates a group by ethnicity")],
        barriers=[BarrierFinding(id=barrier_id,
                                 span="they will never change",
                                 rationale="essentialising binary frame")],
        target_group="migrants",
        themes=["Ethnic Hatred"],
        confidence="medium",
    )


def test_analyze_attaches_promoters_and_label(monkeypatch):
    _fake_llm(monkeypatch, _analysis())
    result = classify.analyze("text", country="Cyprus", age_band="14-17")
    assert result.tier_label == "potential hate speech for human review"
    assert "superordinate_identity" in result.barriers[0].promoters
    assert result.routing is not None          # tier 3 + country -> routing
    assert result.related_cases               # theme lookup hit


def test_analyze_drops_unknown_barrier_ids(monkeypatch):
    _fake_llm(monkeypatch, _analysis(barrier_id="made_up_barrier"))
    result = classify.analyze("text")
    assert result.barriers == []


def test_analyze_no_routing_below_tier3(monkeypatch):
    _fake_llm(monkeypatch, _analysis(tier=2))
    result = classify.analyze("text", country="Cyprus")
    assert result.routing is None


def test_analyze_gates_spans_for_under13(monkeypatch):
    _fake_llm(monkeypatch, _analysis(tier=4))
    result = classify.analyze("text", age_band="10-13")
    assert result.barriers[0].span == "[example withheld for younger learners]"


def test_analyze_drops_invented_citation_ids(monkeypatch):
    analysis = _analysis()
    analysis.rationale = [
        CitationRef(citation_id="cmrec2022-16:def", reason="real"),
        CitationRef(citation_id="totally-made-up-id", reason="invented"),
    ]
    _fake_llm(monkeypatch, analysis)
    result = classify.analyze("text")
    ids = [c.citation_id for c in result.rationale]
    assert ids == ["cmrec2022-16:def"]


def test_analyze_drops_unknown_themes(monkeypatch):
    analysis = _analysis()
    analysis.themes = ["Not A Real Theme"]
    _fake_llm(monkeypatch, analysis)
    result = classify.analyze("text")
    # unknown theme is filtered out -> no theme lookup -> no related cases
    assert result.themes == []
    assert result.related_cases == []


def test_system_tagged_citations_are_not_in_allowlist(monkeypatch):
    analysis = _analysis()
    analysis.rationale.append(
        CitationRef(citation_id="cets225:transparency", reason="system passage"))
    _fake_llm(monkeypatch, analysis)
    result = classify.analyze("text")
    assert all(c.citation_id != "cets225:transparency" for c in result.rationale)
