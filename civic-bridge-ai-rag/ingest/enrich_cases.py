"""Enrich cases.json with appno/date/conclusion from the public HUDOC API,
then assign a theme per case via a single batched LLM call (litellm).

NOTE: 11 entries carry hudoc_match="manual" or theme_source="manual": hand-researched
corrections that live ONLY in the committed cases.json. A from-scratch re-scrape
(Task 2) followed by re-enrichment will lose them; diff against git history if so.
"""
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

import httpx

# Trigger dotenv loading so OPENAI_API_KEY etc. are available for litellm.
from app import config  # noqa: F401

CASES = Path(__file__).resolve().parent.parent / "data" / "knowledge" / "cases.json"
HUDOC = "https://hudoc.echr.coe.int/app/query/results"
SELECT = "itemid,docname,appno,conclusion,kpdate"

THEME_VOCAB: list[str] = [
    "Ethnic Hatred",
    "Anti-semitism",
    "Genocide Denial",
    "LGBTQ",
    "Religious Hatred",
    "Blasphemy",
    "Totalitarianism",
    "Defamation",
    "Totalitarian symbols",
    "Violence",
    "Apology",
    "Violence and religious intolerance",
    "Violence and terrorism",
]

_HEADERS = {"User-Agent": "CivicBridgeAI/1.0 (research; contact paschalidesdemetris@gmail.com)"}


# ---------------------------------------------------------------------------
# HUDOC helpers
# ---------------------------------------------------------------------------

def hudoc_query_url(name: str) -> str:
    """Build a HUDOC search URL for *name* (e.g. 'Leroy v France')."""
    applicant = re.split(r"\sv\.?\s", name)[0].strip()
    query = f'contentsitename:ECHR AND docname:"{applicant}"'
    params = {
        "query": query,
        "select": SELECT,
        "sort": "",
        "start": "0",
        "length": "10",
    }
    return f"{HUDOC}?{urllib.parse.urlencode(params)}"


def _norm(s: str) -> str:
    return re.sub(r"[^a-z]", "", s.lower())


def best_match(name: str, results: list[dict]):
    """Pick the best HUDOC result for *name*.

    Returns (match_dict | None, status) where status is one of:
    'matched', 'ambiguous', 'fuzzy', 'no_match'.
    """
    if not results:
        return None, "no_match"

    parts = re.split(r"\sv\.?\s", name)
    applicant = _norm(parts[0])
    state = _norm(parts[-1]) if len(parts) > 1 else ""

    exact = [
        r for r in results
        if applicant in _norm(r.get("docname", ""))
        and (not state or state in _norm(r.get("docname", "")))
    ]
    if len(exact) >= 1:
        return exact[0], ("matched" if len(exact) == 1 else "ambiguous")
    return results[0], "fuzzy"


def _hudoc_fetch(url: str) -> list[dict]:
    """Fetch HUDOC results and return the list of column dicts."""
    resp = httpx.get(url, timeout=30, headers=_HEADERS)
    resp.raise_for_status()
    data = resp.json()
    return [d["columns"] for d in data.get("results", [])]


# ---------------------------------------------------------------------------
# Theme tagging helpers
# ---------------------------------------------------------------------------

def _apply_theme_mapping(cases: list[dict], mapping: dict[str, str]) -> None:
    """Apply an LLM-returned {case_name: theme} mapping to *cases* in-place.

    Themes not present in THEME_VOCAB are silently dropped (set to "").
    """
    vocab_set = set(THEME_VOCAB)
    for case in cases:
        raw = mapping.get(case["name"], "")
        case["theme"] = raw if raw in vocab_set else ""
        if case["theme"]:
            case["theme_source"] = "llm-assisted"


def tag_themes(cases: list[dict]) -> None:
    """Assign a theme from THEME_VOCAB to each case that currently has theme=="".

    Uses a single batched LLM call (openai/gpt-4.1, temp=0) via litellm.
    Idempotent: skips cases that already have a non-empty theme.
    """
    import litellm  # imported lazily so unit tests don't need it

    untagged = [c for c in cases if not c.get("theme")]
    if not untagged:
        print("tag_themes: all cases already have themes, skipping.")
        return

    vocab_str = json.dumps(THEME_VOCAB)

    lines = []
    for c in untagged:
        conclusion_snippet = (c.get("conclusion") or "")[:200]
        lines.append(f'  {json.dumps(c["name"])}: {json.dumps(conclusion_snippet)}')
    cases_block = "{\n" + ",\n".join(lines) + "\n}"

    prompt = f"""You are a legal analyst specialising in ECHR hate-speech jurisprudence.

Below is a JSON object mapping ECHR case names to their conclusion text (may be empty).
Assign exactly ONE theme from the vocabulary below to each case.
If you are not confident, return "" for that case.

VOCABULARY (use these exact strings):
{vocab_str}

CASES (name -> conclusion excerpt):
{cases_block}

GUIDANCE:
- "Genocide Denial" for cases about denying the Holocaust or other genocides (Garaudy, Honsik, Witzsch, etc.)
- "Anti-semitism" for antisemitic propaganda or speech (Pavel Ivanov, Ivanov v Russia, Kuhnen, etc.)
- "LGBTQ" for homophobic speech or discrimination (Vejdeland, Beizaras, Lilliendahl, etc.)
- "Totalitarianism" for promotion of totalitarian ideologies or parties (Vajnai, Faber, etc.)
- "Totalitarian symbols" for display of totalitarian symbols (Vajnai communist star, etc.)
- "Violence and terrorism" for speech glorifying or inciting violence/terrorism (Leroy cartoon, Stomakhin, etc.)
- "Religious Hatred" for hatred directed at a religion or its members
- "Blasphemy" for offensive speech about a religion itself (I.A v Turkey, Giniewski, etc.)
- "Ethnic Hatred" for hatred of an ethnic group (Féret, Belkacem, Soulas, Jersild, etc.)
- "Defamation" for defamation cases involving public figures
- "Apology" for cases involving apology/glorification of past crimes
- "Violence" for incitement to violence not covered by terrorism theme
- "Violence and religious intolerance" for overlap of violence and religious hatred

Respond with ONLY a valid JSON object: {{"case name": "theme", ...}}
No explanation, no markdown fences.
"""

    try:
        response = litellm.completion(
            model="openai/gpt-4.1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            timeout=60,
        )
    except Exception as exc:
        print(f"tag_themes: LLM call failed, themes left empty: {exc}")
        return
    raw_text = response.choices[0].message.content.strip()

    # Strip markdown code fences if present
    raw_text = re.sub(r"^```(?:json)?\n?", "", raw_text)
    raw_text = re.sub(r"\n?```$", "", raw_text)

    try:
        mapping = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        print(f"tag_themes: JSON parse error: {exc}\nRaw response:\n{raw_text[:500]}")
        return

    if not isinstance(mapping, dict):
        print(f"tag_themes: unexpected response type {type(mapping)}")
        return

    _apply_theme_mapping(untagged, mapping)

    tagged = sum(1 for c in untagged if c.get("theme"))
    print(f"tag_themes: tagged {tagged}/{len(untagged)} cases")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    cases = json.loads(CASES.read_text())

    # --- Part A: HUDOC enrichment ---
    enriched = 0
    for case in cases:
        if case["hudoc_match"] not in ("unenriched", "no_match"):
            continue
        url = hudoc_query_url(case["name"])
        try:
            results = _hudoc_fetch(url)
        except Exception as exc:
            print(f"  HUDOC error for {case['name']}: {exc}")
            continue
        match, status = best_match(case["name"], results)
        case["hudoc_match"] = status
        if match:
            case["appno"] = match.get("appno", "")
            case["date"] = (match.get("kpdate") or "")[:10]
            case["conclusion"] = match.get("conclusion", "")
            enriched += 1
        time.sleep(0.5)

    CASES.write_text(json.dumps(cases, indent=2, ensure_ascii=False))

    flagged = [c["name"] for c in cases if c["hudoc_match"] in ("ambiguous", "fuzzy", "no_match")]
    print(f"enriched {enriched}/{len(cases)}; review flagged: {len(flagged)}")
    for name in flagged:
        print(f"  FLAG [{cases[[c['name'] for c in cases].index(name)]['hudoc_match']}]: {name}")

    # --- Part B: LLM-assisted theme tagging ---
    print("\nRunning LLM theme tagging...")
    tag_themes(cases)
    CASES.write_text(json.dumps(cases, indent=2, ensure_ascii=False))

    # Print theme coverage
    themed = [c for c in cases if c.get("theme")]
    print(f"\nTheme coverage: {len(themed)}/{len(cases)} ({100*len(themed)//len(cases)}%)")

    # Anchor verification
    anchors = {
        "Garaudy v France": "Genocide Denial",
        "Vejdeland and others v Sweden": "LGBTQ",
        "Leroy v France": "Violence and terrorism",
        "Ivanov v Russia": "Anti-semitism",
    }
    print("\nAnchor verification:")
    for name, expected in anchors.items():
        match_case = next((c for c in cases if c["name"] == name), None)
        if match_case:
            got = match_case.get("theme", "")
            status = "OK" if got == expected else f"MISMATCH (got '{got}')"
            print(f"  {name}: {status}")
        else:
            print(f"  {name}: NOT FOUND in cases.json")

    return 0


if __name__ == "__main__":
    sys.exit(main())
