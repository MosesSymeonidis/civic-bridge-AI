import app.extract as extract
from app.extract import extract_quoted, llm_extract


def test_extract_quoted_double_quotes():
    msg = ('A student showed me this: "They will never change, it is in their '
           'nature, every single one of them." What now?')
    res = extract_quoted(msg)
    assert res is not None
    text, raw = res
    assert text.startswith("They will never change")
    assert raw in msg


def test_extract_quoted_blockquote():
    msg = ("What is this?\n"
           "> They are flooding our schools\n"
           "> and they do not belong here.\n"
           "Is it hate speech?")
    text, raw = extract_quoted(msg)
    assert "flooding our schools" in text
    assert raw in msg


def test_extract_quoted_none_for_plain_question():
    assert extract_quoted("What does ECRI say about Cyprus?") is None
    # Short quotes are conversational, not pasted posts.
    assert extract_quoted('He said "no way" to me.') is None


def test_llm_extract_rejects_non_verbatim(monkeypatch):
    msg = ("Someone commented They will never change, it is in their nature. "
           "What do you think?")
    monkeypatch.setattr(
        extract.llm, "complete",
        lambda *a, **k: extract._Extraction(
            contains_post=True, post_text="They are all evil monsters"))
    assert llm_extract(msg) is None


def test_llm_extract_accepts_verbatim(monkeypatch):
    msg = ("Someone commented: They will never change, it is in their nature. "
           "What do you think?")
    monkeypatch.setattr(
        extract.llm, "complete",
        lambda *a, **k: extract._Extraction(
            contains_post=True,
            post_text="They will never change, it is in their nature."))
    assert llm_extract(msg) == "They will never change, it is in their nature."


def test_llm_extract_any_failure_degrades_to_none(monkeypatch):
    monkeypatch.setattr(extract.llm, "complete",
                        lambda *a, **k: "not a model instance")
    assert llm_extract("a message that is comfortably long enough") is None
