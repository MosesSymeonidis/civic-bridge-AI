import pytest
from pydantic import BaseModel

import app.llm as llm


class Out(BaseModel):
    answer: str


def _resp(content):
    class Msg:  # mimic litellm response shape
        pass
    m = Msg(); m.content = content
    c = Msg(); c.message = m
    r = Msg(); r.choices = [c]
    return r


def test_complete_plain_text(monkeypatch):
    monkeypatch.setattr(llm.litellm, "completion", lambda **kw: _resp("hello"))
    assert llm.complete([{"role": "user", "content": "hi"}]) == "hello"


def test_complete_schema_repairs_bad_json(monkeypatch):
    calls = []

    def fake(**kw):
        calls.append(kw)
        # {"wrong_key": "x"} genuinely fails pydantic v2 (missing required field)
        return _resp('{"wrong_key": "x"}' if len(calls) == 1 else '{"answer": "ok"}')

    monkeypatch.setattr(llm.litellm, "completion", fake)
    out = llm.complete([{"role": "user", "content": "hi"}], schema=Out)
    assert out.answer == "ok" and len(calls) == 2


def test_complete_falls_back_to_next_model(monkeypatch):
    def fake(**kw):
        if kw["model"] == "m1":
            raise RuntimeError("down")
        return _resp("from m2")

    monkeypatch.setattr(llm.litellm, "completion", fake)
    assert llm.complete([{"role": "user", "content": "hi"}], models=["m1", "m2"]) == "from m2"


def test_all_models_fail(monkeypatch):
    def fake(**kw):
        raise RuntimeError("down")
    monkeypatch.setattr(llm.litellm, "completion", fake)
    with pytest.raises(llm.LLMError):
        llm.complete([{"role": "user", "content": "hi"}], models=["m1"])


def test_repair_failure_falls_through_to_next_model(monkeypatch):
    calls = []

    def fake(**kw):
        calls.append(kw["model"])
        if kw["model"] == "m1":
            return _resp('{"wrong_key": "x"}')  # invalid on initial AND repair
        return _resp('{"answer": "from m2"}')

    monkeypatch.setattr(llm.litellm, "completion", fake)
    out = llm.complete([{"role": "user", "content": "hi"}],
                       schema=Out, models=["m1", "m2"])
    assert out.answer == "from m2"
    assert calls == ["m1", "m1", "m2"]
