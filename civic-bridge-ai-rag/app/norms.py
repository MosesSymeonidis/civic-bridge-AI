from collections.abc import Set as AbstractSet

import yaml

from app import config
from app.source_documents import SOURCE_DOCUMENTS

_CACHE: dict | None = None

_CITATION_DOCUMENTS = {
    "cmrec2022-16": "cmrec2022-16.pdf",
    "cets189": "CETS_189.docx.pdf",
    "cets225": "CETS_225_EN.docx.pdf",
    "echr": "ECHR Art. 10.pdf",
}


def load_norms() -> dict:
    global _CACHE
    if _CACHE is None:
        _CACHE = yaml.safe_load((config.KNOWLEDGE / "norms_core.yaml").read_text())
        ids = [p["id"] for p in _CACHE["passages"]]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate citation IDs in norms_core.yaml")
    return _CACHE


def norms_block(exclude_tags: AbstractSet[str] = frozenset({"system"})) -> str:
    norms = load_norms()
    lines = [
        f'[{p["id"]}] ({p["source"]}) {p["text"]}'
        for p in norms["passages"]
        if not (set(p.get("tags", [])) & exclude_tags)
    ]
    return "\n".join(lines)


def tier_label(tier: int) -> str:
    tiers = load_norms()["tiers"]
    if tier not in tiers:
        raise ValueError(f"tier {tier!r} not in tiers dict (valid: {list(tiers)})")
    return tiers[tier]


def passages_by_tag(tag: str) -> list[dict]:
    return [p for p in load_norms()["passages"] if tag in p.get("tags", [])]


def citation_reference(citation_id: str) -> dict | None:
    passage = next(
        (p for p in load_norms()["passages"] if p["id"] == citation_id),
        None,
    )
    if passage is None:
        return None

    prefix = citation_id.split(":", 1)[0]
    filename = _CITATION_DOCUMENTS.get(prefix)
    document = SOURCE_DOCUMENTS.get(filename, {}) if filename else {}
    return {
        "id": citation_id,
        "title": passage["source"],
        "url": document.get("url", ""),
        "file": f"data/raw/legal/{filename}" if filename else "",
    }
