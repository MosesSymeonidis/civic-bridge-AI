from app.safety import (triage_flag, is_under13, gate_spans,
                        soften_determinations)


def test_triage_triggers_on_first_person_targeting():
    assert triage_flag("they keep posting things about me at school")
    assert triage_flag("I am the one they are talking about and I'm scared")
    assert triage_flag("someone keeps sending me these messages every day")


def test_triage_ignores_third_person_analysis():
    assert not triage_flag("I saw this post about migrants, is it hate speech?")
    assert not triage_flag("My students found this comment online.")


def test_under13_bands():
    assert is_under13("6-9") and is_under13("10-13")
    assert not is_under13("14-17") and not is_under13("18+")


def test_gate_spans_redacts_tier4_for_under13():
    spans = ["they should all be driven out"]
    assert gate_spans(spans, tier=4, age_band="10-13") == ["[example withheld for younger learners]"]
    assert gate_spans(spans, tier=4, age_band="14-17") == spans
    assert gate_spans(spans, tier=2, age_band="6-9") == spans


def test_soften_determinations():
    out = soften_determinations("This post is illegal and is a crime.")
    assert "illegal" not in out and "crime" not in out
    assert "human review" in out or "authorities" in out


# ─── Controller-required extra test cases ─────────────────────────────────────

def test_triage_greek_cypriot_context_positive():
    # First-person targeting without the literal stand-alone word "me":
    # "at me" fires the \bat me\b pattern — covers the "laughs at me" phrasing
    # common when describing online ridicule after a photo is tagged.
    assert triage_flag(
        "they wrote my name under the photo and now everyone laughs at me"
    )
    # Also covers a variant where the person says they feel targeted at school
    assert triage_flag(
        "some kids at school are spreading photos of me and I feel unsafe"
    )


def test_triage_teacher_message_negative():
    # A teacher asking for advice: "showed me" uses "showed", which is NOT in
    # the send/post/message keyword list, so the send-pattern does not fire.
    # "post" appears but no \bme\b follows within 40 chars of it.
    assert not triage_flag("a student showed me this post, what should I do?")
    # Another plausible educator phrasing — no self-targeting signals
    assert not triage_flag("My class encountered this example of hate speech today.")


def test_triage_first_person_avoidance_distress_positive():
    # Avoidance of school/spaces due to online harassment is a strong signal
    # of first-person targeting even without "me" as the direct object.
    # Caught by the \bdon'?t want to (go to|come to|be at) school\b pattern.
    assert triage_flag(
        "i don't want to go to school anymore because of what they post"
    )
    # Variant using "can't go" phrasing
    assert triage_flag(
        "i can't go back to school because of what they're saying about me online"
    )


def test_soften_determinations_plural_forms():
    out = soften_determinations("These posts are illegal and are crimes.")
    assert "illegal" not in out and "crime" not in out


def test_soften_plural_keeps_verb_agreement():
    out = soften_determinations("These posts are illegal.")
    assert "These posts show signals" in out


def test_soften_adverb_qualified_determinations():
    for phrase in ["This is clearly illegal.", "That post is probably illegal.",
                   "These are obviously illegal."]:
        assert "illegal" not in soften_determinations(phrase), phrase
