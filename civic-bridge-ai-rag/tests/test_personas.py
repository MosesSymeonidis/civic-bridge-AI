import pytest

from app.personas import system_prompt, triage_response


def test_system_prompt_layers_role_and_age():
    p = system_prompt(role="student", age_band="10-13", country="Cyprus")
    assert "answering the student's immediate question directly" in p
    assert "practical plan" in p
    assert "at most one question" in p
    assert "Never recommend a specific" in p
    assert "punishment such as suspension or expulsion" in p
    assert "never decide whether speech is unlawful" in p.lower() or "never determine" in p.lower()
    assert "Cyprus" in p


def test_teacher_prompt_mentions_rfcdc_and_toggle():
    p = system_prompt(role="teacher", age_band="14-17", country="Cyprus")
    assert "RFCDC" in p
    assert "teaching opportunity" in p


def test_teacher_prompt_supports_mixed_age_groups():
    p = system_prompt(role="teacher", age_band="mixed", country="Cyprus")
    assert "multiple age bands" in p


def test_teacher_prompt_answers_definition_questions_directly():
    p = system_prompt(role="teacher", age_band="14-17", country="Cyprus")
    assert "definition or explanation question" in p
    assert "answer directly first" in p
    assert "at most one follow-up question" in p


def test_triage_response_includes_helplines():
    msg = triage_response(country="Cyprus", age_band="10-13")
    assert "trusted adult" in msg.lower()
    assert "116" in msg.replace(" ", "")


def test_system_prompt_rejects_unknown_role():
    with pytest.raises(ValueError):
        system_prompt(role="wizard", age_band="10-13", country="Cyprus")


def test_system_prompt_rejects_unknown_age_band():
    with pytest.raises(ValueError):
        system_prompt(role="student", age_band="40-50", country="Cyprus")
