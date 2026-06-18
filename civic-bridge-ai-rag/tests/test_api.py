from fastapi.testclient import TestClient

import app.main as main
from app.classify import AnalysisResult

client = TestClient(main.app)


def test_registry_endpoint():
    resp = client.get("/registry/Cyprus")
    assert resp.status_code == 200
    assert resp.json()["verified"] is True


def test_registry_unknown_404():
    assert client.get("/registry/Atlantis").status_code == 404


def test_analyze_endpoint(monkeypatch):
    fake = AnalysisResult(tier=1, tier_label="ordinary political expression",
                          rationale=[], barriers=[], target_group="none")
    monkeypatch.setattr(main.classify, "analyze", lambda *a, **k: fake)
    resp = client.post("/analyze", json={"text": "I disagree with this policy."})
    assert resp.status_code == 200
    assert resp.json()["tier"] == 1


def test_analyze_validates_age_band():
    resp = client.post("/analyze", json={"text": "x", "age_band": "5-7"})
    assert resp.status_code == 422


def test_chat_endpoint(monkeypatch):
    monkeypatch.setattr(main.chat, "handle",
                        lambda **kw: {"reply": "hi", "analysis": None,
                                      "citations": [], "triage": False})
    resp = client.post("/chat", json={
        "session_id": "t1", "role": "teacher", "age_band": "18+",
        "country": "Cyprus", "message": "hello"})
    assert resp.json()["reply"] == "hi"


def test_chat_endpoint_processes_image_with_prompt(monkeypatch):
    seen = {}

    def fake_extract_text(image, mime_type=None, user_prompt=None):
        seen["image"] = image
        seen["mime_type"] = mime_type
        seen["user_prompt"] = user_prompt
        return "Text extracted from the screenshot."

    def fake_handle(**kw):
        seen["chat"] = kw
        return {"reply": "hi", "analysis": None, "citations": [], "triage": False}

    monkeypatch.setattr(main.image_text, "extract_text", fake_extract_text)
    monkeypatch.setattr(main.chat, "handle", fake_handle)

    resp = client.post("/chat", json={
        "session_id": "t1",
        "role": "teacher",
        "age_band": "18+",
        "country": "Cyprus",
        "message": "What does this post mean?",
        "image": {
            "image": "data:image/png;base64,aGVsbG8=",
            "filename": "screenshot.png",
            "mime_type": "image/png",
        },
    })

    assert resp.status_code == 200
    assert seen["image"].startswith("data:image/png;base64,")
    assert seen["mime_type"] == "image/png"
    assert seen["user_prompt"] == "What does this post mean?"
    assert seen["chat"]["attachment"] == "Text extracted from the screenshot."


def test_report_endpoint(monkeypatch):
    monkeypatch.setattr(main.reports, "create_report",
                        lambda **kw: {"id": 1, "draft": "DRAFT"})
    resp = client.post("/report", json={
        "text": "post", "country": "Cyprus", "role": "teacher",
        "tier": 3, "tier_label": "potential hate speech for human review",
        "rationale": []})
    assert resp.json()["id"] == 1


def test_stats_endpoint():
    resp = client.get("/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert "by_tier" in body and "privacy_note" in body
