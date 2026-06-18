from pathlib import Path

from app import config, registry

PROMPTS = Path(__file__).parent / "prompts"

# NOTE: prompt files are rendered with str.format() to inject {country},
# {age_band} and {helplines}. They must therefore stay free of any other
# literal curly braces, which str.format() would treat as fields and choke on.
# Keep prompt copy brace-free.


def _read(name: str) -> str:
    return (PROMPTS / name).read_text()


def system_prompt(role: str, age_band: str, country: str) -> str:
    if role not in config.ROLES:
        raise ValueError(
            f"unknown role {role!r}; expected one of {config.ROLES}"
        )
    if age_band not in config.AGE_BANDS:
        raise ValueError(
            f"unknown age_band {age_band!r}; expected one of {config.AGE_BANDS}"
        )
    base = _read("base.md").format(country=country)
    persona = _read(f"{role}.md").format(age_band=age_band)
    age = _read(f"age_{age_band}.md")
    return "\n\n".join([base, persona, age])


def triage_response(country: str, age_band: str) -> str:
    # age_band is accepted but intentionally unused for now: the safety copy is
    # deliberately uniform across bands (reviewed as readable from ~10 up). If
    # a simplified 6-9 variant is added later, branch on it here.
    lines = registry.helplines(country)
    formatted = "\n".join(
        f"- You can call {h['name']}: {h['phone']} (free, for {h['audience']})."
        for h in lines
    ) or "- You can look up your country's child helpline at 116111.eu."
    return _read("triage_response.md").format(helplines=formatted)
