import app.chat as chat
from app.classify import AnalysisResult, CitationRef


def setup_function():
    chat.SESSIONS.clear()


def test_student_triage_pivots_before_analysis(monkeypatch):
    called = []
    monkeypatch.setattr(chat.classify, "analyze",
                        lambda *a, **k: called.append(1))
    out = chat.handle(session_id="s1", role="student", age_band="10-13",
                      country="Cyprus",
                      message="they keep posting things about me and I'm scared",
                      attachment="some nasty post")
    assert called == []                      # analysis NOT run
    assert "trusted adult" in out["reply"].lower()
    assert chat.SESSIONS["s1"]["state"] == "triage"


def test_attachment_triggers_analysis(monkeypatch):
    fake = AnalysisResult(tier=2, tier_label="offensive or harmful expression",
                          rationale=[CitationRef(citation_id="echr:offend-shock-disturb",
                                                 reason="offensive but protected")],
                          barriers=[], target_group="none", themes=[])
    monkeypatch.setattr(chat.classify, "analyze", lambda *a, **k: fake)
    monkeypatch.setattr(chat.llm, "complete",
                        lambda messages, **kw: "Let us look at this together. [echr:offend-shock-disturb]")
    out = chat.handle(session_id="s2", role="teacher", age_band="14-17",
                      country="Cyprus", message="what do you make of this?",
                      attachment="some post text")
    assert out["analysis"]["tier"] == 2
    assert out["summary"] is None
    assert "[echr:offend-shock-disturb]" in out["reply"]
    assert out["references"][0]["id"] == "echr:offend-shock-disturb"
    assert out["references"][0]["url"].startswith("https://")
    assert out["references"][0]["file"].endswith("ECHR Art. 10.pdf")


def test_open_question_uses_retrieval(monkeypatch):
    monkeypatch.setattr(chat.retrieval, "search",
                        lambda q, k=4: [{"text": "ECRI notes...",
                                        "source": "ECRI Annual Report 2025",
                                        "page": 9,
                                        "url": "https://example.test/ecri"}])
    monkeypatch.setattr(chat.llm, "complete",
                        lambda messages, **kw: "ECRI reports that... [S1]")
    out = chat.handle(session_id="s3", role="teacher", age_band="18+",
                      country="Cyprus", message="what does ECRI say about Cyprus?")
    assert out["citations"][0]["source"] == "ECRI Annual Report 2025"
    assert out["references"] == [{
        "id": "S1",
        "title": "ECRI Annual Report 2025",
        "url": "https://example.test/ecri",
        "file": "",
        "locator": "p.9",
        "excerpt": "ECRI notes...",
    }]


def test_response_references_rewrite_octopus_good_practices_url():
    references = chat._response_references(
        citations=[{
            "source": "Octopus Good Practice Study",
            "url": "https://www.coe.int/en/web/octopus/good-practices",
        }],
        analysis=None,
        reporting=None,
    )

    assert references[0]["url"] == "https://www.coe.int/en/web/octopus/"


def test_output_guard_softens_determinations(monkeypatch):
    monkeypatch.setattr(chat.retrieval, "search", lambda q, k=4: [])
    monkeypatch.setattr(chat.llm, "complete",
                        lambda messages, **kw: "This post is illegal.")
    out = chat.handle(session_id="s4", role="teacher", age_band="18+",
                      country="Cyprus", message="is this illegal?")
    assert "illegal" not in out["reply"]


def test_post_triage_turn_carries_targeted_note(monkeypatch):
    """Once a student is in triage state, subsequent turns do not re-trigger
    and the system prompt gains a gentle 'personally targeted' note."""
    seen = {}
    monkeypatch.setattr(chat.retrieval, "search", lambda q, k=4: [])

    def fake_complete(messages, **kw):
        seen["system"] = messages[0]["content"]
        return "Of course, let us look at this gently."

    monkeypatch.setattr(chat.llm, "complete", fake_complete)

    # First turn trips triage (no LLM).
    chat.handle(session_id="s5", role="student", age_band="10-13",
                country="Cyprus", message="they keep saying things about me")
    assert chat.SESSIONS["s5"]["state"] == "triage"

    # Second turn: student asks to continue; must NOT re-trigger, must call LLM.
    out = chat.handle(session_id="s5", role="student", age_band="10-13",
                      country="Cyprus", message="can you help me understand it?")
    assert out["triage"] is False
    assert "personally targeted" in seen["system"]


def test_inline_quoted_post_triggers_analysis(monkeypatch):
    fake = AnalysisResult(tier=3, tier_label="potential hate speech for human review",
                          rationale=[], barriers=[], target_group="migrants")
    seen = {}

    def fake_analyze(text, **kw):
        seen["text"] = text
        return fake

    monkeypatch.setattr(chat.classify, "analyze", fake_analyze)
    monkeypatch.setattr(chat.llm, "complete", lambda messages, **kw: "Here is what I see.")
    out = chat.handle(session_id="q1", role="teacher", age_band="14-17",
                      country="Cyprus",
                      message='A student showed me this comment: "They will never '
                              'change, it is in their nature, every single one of '
                              'them." What am I looking at?')
    assert out["analysis"]["tier"] == 3
    assert seen["text"].startswith("They will never change")


def test_high_severity_analysis_stores_country_reporting_without_showing_it(monkeypatch):
    fake = AnalysisResult(tier=4, tier_label="high-severity incitement/dehumanisation risk",
                          rationale=[], barriers=[], target_group="African descent",
                          themes=[])
    monkeypatch.setattr(chat.classify, "analyze", lambda *a, **k: fake)
    monkeypatch.setattr(chat.llm, "complete", lambda messages, **kw: "Here is what I see.")

    out = chat.handle(session_id="r1", role="teacher", age_band="14-17",
                      country="Cyprus", message="what do you make of this?",
                      attachment="leave, monkey, leave")

    assert out["reporting"] is None
    assert chat.SESSIONS["r1"]["last_reporting"]["country"] == "Cyprus"


def test_reporting_followup_uses_stored_country_contacts(monkeypatch):
    fake = AnalysisResult(tier=4, tier_label="high-severity incitement/dehumanisation risk",
                          rationale=[], barriers=[], target_group="African descent",
                          themes=[])
    seen = {}
    monkeypatch.setattr(chat.classify, "analyze", lambda *a, **k: fake)
    monkeypatch.setattr(chat.extract, "llm_extract", lambda message: None)
    monkeypatch.setattr(chat.retrieval, "search", lambda q, k=4: [])

    def fake_complete(messages, **kw):
        seen["last_user"] = messages[-1]["content"]
        return "Use the Cyprus contacts listed."

    monkeypatch.setattr(chat.llm, "complete", fake_complete)

    chat.handle(session_id="r2", role="teacher", age_band="14-17",
                country="Cyprus", message="what do you make of this?",
                attachment="leave, monkey, leave")
    out = chat.handle(session_id="r2", role="teacher", age_band="14-17",
                      country="Cyprus", message="Let's go with c, how do I report this?")

    assert out["analysis"] is None
    assert out["reporting"]["equality_body"]["name"].startswith("Commissioner")
    assert "COUNTRY-SPECIFIC REPORTING CONTACTS" in seen["last_user"]
    assert "CYberSafety Helpline" in seen["last_user"]


def test_student_quoted_distress_words_do_not_trigger_triage(monkeypatch):
    fake = AnalysisResult(tier=2, tier_label="offensive or harmful expression",
                          rationale=[], barriers=[], target_group="none")
    monkeypatch.setattr(chat.classify, "analyze", lambda *a, **k: fake)
    monkeypatch.setattr(chat.llm, "complete", lambda messages, **kw: "Let us think about it.")
    out = chat.handle(session_id="q2", role="student", age_band="14-17",
                      country="Cyprus",
                      message='I found this comment online: "we keep posting about '
                              'me says the scared little snitch, every day". '
                              'Can we look at it together?')
    assert out["triage"] is False
    assert out["summary"]


def test_student_distress_triage_runs_without_any_llm(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("LLM must not be called on the triage path")

    monkeypatch.setattr(chat.llm, "complete", boom)
    out = chat.handle(session_id="q3", role="student", age_band="10-13",
                      country="Cyprus",
                      message="they keep posting things about me and I'm scared")
    assert out["triage"] is True
