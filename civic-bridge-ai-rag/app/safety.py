"""Code-enforced safety: triage screen, age gating, no-determination guard.

These run on inputs/outputs regardless of what any prompt does.
"""
import re

TRIAGE_PATTERNS = [
    # Direct object: "about me", "at me"
    r"\babout me\b",
    r"\bat me\b",
    r"\btargeting me\b",

    # "I'm the one / I'm the target / I'm the victim" (requires apostrophe form)
    r"\bi'?m (the )?(one|target|victim)\b",

    # Communication directed at the person: send/post/message + "me" within 40 non-period chars.
    # "showed" is deliberately excluded to avoid false positives from teachers
    # saying "a student showed me this post".
    r"\b(send|sending|sent|post|posting|message|messaging|messages)\b[^.]{0,40}\bme\b",

    # "keep/keeps ... me/us" — ongoing harassment pattern
    r"\bkeep[s]?\b[^.]{0,40}\b(me|us)\b",

    # Distress keywords in first-person contexts
    r"\b(scared|afraid|frightened|threatened|unsafe)\b",

    # "won't stop" — persistent harassment signal
    r"\bwon'?t stop\b",

    # "every day ... me/us" — frequency + target pattern
    r"\bevery ?day\b[^.]{0,40}\b(me|us)\b",

    # First-person school avoidance — strong signal of ongoing personal targeting.
    # "don't want to go to school" and "can't go/come back to school" are
    # almost exclusively said by the person being harassed, not an observer.
    # False-positive risk: low; an educator would say "a student doesn't want
    # to go to school" (third person), not the first-person form.
    r"\b(don'?t want to go|can'?t (go|come) back) to school\b",
]
_TRIAGE_RE = [re.compile(p, re.I) for p in TRIAGE_PATTERNS]

REDACTION = "[example withheld for younger learners]"

_DETERMINATION_SUBS = [
    (re.compile(r"\b(?:is |are )?(?:clearly|probably|definitely|obviously|technically) illegal\b", re.I),
     "shows signals that authorities and courts would need to assess"),
    (re.compile(r"\bis illegal\b", re.I),
     "shows signals that authorities and courts would need to assess"),
    (re.compile(r"\bare illegal\b", re.I),
     "show signals that authorities and courts would need to assess"),
    (re.compile(r"\b(is a|are) crimes?\b", re.I),
     "may fall within categories that only authorities can determine"),
    (re.compile(r"\bis (a )?crime\b", re.I),
     "may fall within categories that only authorities can determine"),
    (re.compile(r"\bbreaks the law\b", re.I),
     "raises questions that require human legal review"),
    (re.compile(r"\bis unlawful\b", re.I),
     "shows risk signals requiring human review"),
]


def triage_flag(message: str) -> bool:
    """Return True if the message contains signals that the sender is
    personally targeted by harassment or hate speech.

    CONTRACT: call this only for role == "student". The patterns are
    recall-biased and include bare distress keywords that routinely appear in
    third-person analyst/teacher phrasings ("makes refugees feel unsafe");
    gating by role at the call site is what keeps those from misrouting.

    Bias toward sensitivity (recall) over precision: a false negative
    means a child describing their own harassment gets an academic
    analysis instead of a safety check-in. A false positive costs one
    gentle check-in message.
    """
    return any(rx.search(message) for rx in _TRIAGE_RE)


def is_under13(age_band: str) -> bool:
    """Return True for age bands representing children under 13."""
    return age_band in {"6-9", "10-13"}


def gate_spans(spans: list[str], tier: int, age_band: str | None) -> list[str]:
    """Redact severe-tier (tier >= 4) example spans for under-13 learners.

    Lower tiers and older age bands pass through unchanged.
    """
    if tier >= 4 and age_band and is_under13(age_band):
        return [REDACTION for _ in spans]
    return spans


def soften_determinations(text: str) -> str:
    """Replace direct legal determinations with appropriately hedged language.

    The system must never assert illegality or criminality — those are
    determinations for human authorities and courts, not an AI classifier.
    """
    for rx, replacement in _DETERMINATION_SUBS:
        text = rx.sub(replacement, text)
    return text
