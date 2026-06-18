import copy
import json
import urllib.parse

from app import config

_AUTH: dict | None = None
_CASES: list | None = None


def _load_auth() -> dict:
    global _AUTH
    if _AUTH is None:
        _AUTH = json.loads((config.KNOWLEDGE / "authorities.json").read_text())
    return _AUTH


def _load_cases() -> list:
    global _CASES
    if _CASES is None:
        _CASES = json.loads((config.KNOWLEDGE / "cases.json").read_text())
    return _CASES


def authorities(country: str) -> dict:
    """Return a deep copy of the authority record for *country*.

    Raises KeyError for unknown countries so callers (e.g. an HTTP endpoint)
    can map it to a 404 without extra logic.
    """
    data = _load_auth()
    if country not in data:
        raise KeyError(country)
    return copy.deepcopy(data[country])


def helplines(country: str) -> list[dict]:
    """Return helpline entries for *country*, or [] if none / unknown country."""
    try:
        return [dict(h) for h in authorities(country).get("helplines", [])]
    except KeyError:
        return []


def _hudoc_case_url(case: dict) -> str:
    appno = (case.get("appno") or "").split(";")[0].strip()
    query = f'appno="{appno}"' if appno else f'docname="{case.get("name", "")}"'
    return "https://hudoc.echr.coe.int/eng#" + urllib.parse.quote(
        json.dumps({"query": query})
    )


def cases_by_theme(themes: list[str], limit: int = 3) -> list[dict]:
    """Return up to *limit* cases whose theme matches any entry in *themes*.

    Only cases with a non-empty ``conclusion`` are included.
    Returns shallow copies of the matched dicts so callers cannot mutate
    the cached list.
    """
    wanted = {t.lower() for t in themes}
    hits = [
        dict(c)
        for c in _load_cases()
        if c.get("theme", "").lower() in wanted and c.get("conclusion")
    ]
    for case in hits:
        case.setdefault("url", _hudoc_case_url(case))
    return hits[:limit]
