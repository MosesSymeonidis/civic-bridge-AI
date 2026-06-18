"""Find third-party content (a pasted post) inside a single chat message.

Two mechanisms, used in this order by the chat layer:
1. extract_quoted: deterministic, no LLM. Quoted blocks ("..." or > lines) are
   treated as the post. Returns (post_text, raw_segment) so the caller can also
   strip the segment before running the student triage screen (the harasser's
   words inside a quote must not trigger the student's own safety pivot).
2. llm_extract: one small LLM call for unquoted pastes, guarded by a verbatim
   substring check so the model cannot invent content that was never sent.
"""
import re

from pydantic import BaseModel

from app import llm

# A double-quoted span of at least 40 chars (straight or curly quotes).
_QUOTE_RE = re.compile(r'["“]([^"“”]{40,})["”]', re.S)
# One or more consecutive markdown blockquote lines.
_BLOCKQUOTE_RE = re.compile(r"((?:^[ \t]*>.*(?:\n|$))+)", re.M)

MIN_POST_CHARS = 20


class _Extraction(BaseModel):
    contains_post: bool
    post_text: str = ""


_EXTRACT_PROMPT = """The user message below may contain third-party content the
user wants analysed: a social media post, comment, or something someone else
wrote or said. Decide whether it does.

If yes, copy the third-party content EXACTLY as it appears in the message,
character for character. Do not include the user's own question, framing, or
description. If the message is only the user's own words (a question, a
description of a situation, a request), there is no post.

Respond with JSON only: {"contains_post": true|false, "post_text": "..."}"""


def _squash(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def extract_quoted(message: str) -> tuple[str, str] | None:
    """Deterministic extraction. Returns (post_text, raw_segment) or None."""
    m = _BLOCKQUOTE_RE.search(message)
    if m:
        text = re.sub(r"^[ \t]*> ?", "", m.group(1), flags=re.M).strip()
        if len(text) >= MIN_POST_CHARS:
            return text, m.group(1)
    m = _QUOTE_RE.search(message)
    if m:
        return m.group(1).strip(), m.group(0)
    return None


def llm_extract(message: str) -> str | None:
    """LLM extraction with a verbatim-substring hallucination guard.

    Best-effort by design: ANY failure (provider down, schema mismatch, an
    unexpected response shape) degrades to "no post found" so the chat falls
    back to the retrieval path instead of erroring.
    """
    try:
        out: _Extraction = llm.complete(
            [{"role": "system", "content": _EXTRACT_PROMPT},
             {"role": "user", "content": message}],
            schema=_Extraction, temperature=0,
        )
        candidate = out.post_text.strip()
        contains = out.contains_post
    except Exception:
        return None
    if not contains or len(candidate) < MIN_POST_CHARS:
        return None
    if _squash(candidate) not in _squash(message):
        return None  # model paraphrased or invented; refuse
    return candidate
