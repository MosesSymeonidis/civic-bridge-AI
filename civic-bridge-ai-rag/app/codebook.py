import json

from app import config

_CACHE: dict | None = None


def load_codebook() -> dict:
    global _CACHE
    if _CACHE is None:
        cb = json.loads((config.KNOWLEDGE / "codebook.json").read_text())
        promoter_ids = set(cb["promoters"])
        for bid, b in cb["barriers"].items():
            # Referential integrity: every promoter a barrier maps to must exist.
            for pid in b["promoters"]:
                if pid not in promoter_ids:
                    raise ValueError(
                        f"barrier {bid!r} references unknown promoter {pid!r}"
                    )
            # Each example span must be an exact substring of its example text.
            for ex in b["examples"]:
                if ex["span"] not in ex["text"]:
                    raise ValueError(
                        f"barrier {bid!r} example span {ex['span']!r} "
                        f"is not a substring of its text"
                    )
        _CACHE = cb
    return _CACHE


def promoters_for(barrier_id: str) -> list[str]:
    # Copy so callers can't mutate the cached codebook through the reference.
    return list(load_codebook()["barriers"][barrier_id]["promoters"])


def activities_for(barrier_id: str, age_band: str) -> str:
    return load_codebook()["barriers"][barrier_id]["activities"][age_band]


def promoter_guidance(promoter_id: str) -> dict:
    return dict(load_codebook()["promoters"][promoter_id])


def codebook_block() -> str:
    cb = load_codebook()
    lines = []
    for bid, b in cb["barriers"].items():
        markers = ", ".join(b["markers"])
        examples = " | ".join(
            f'"{e["span"]}" ({e["note"]})' for e in b["examples"]
        )
        lines.append(
            f"BARRIER {bid} ({b['label']}): {b['definition']} "
            f"Markers: {markers}. Examples: {examples}"
        )
    return "\n".join(lines)
