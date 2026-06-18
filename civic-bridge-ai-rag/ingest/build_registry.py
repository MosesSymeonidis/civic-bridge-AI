"""Build data/knowledge/authorities.json: 46 CoE states, Cyprus hand-verified."""
import json
import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

OUT = Path(__file__).resolve().parent.parent / "data" / "knowledge" / "authorities.json"
EQUINET_URL = "https://equineteurope.org/who-we-are/our-members/"

COE_STATES = [
    "Albania", "Andorra", "Armenia", "Austria", "Azerbaijan", "Belgium",
    "Bosnia and Herzegovina", "Bulgaria", "Croatia", "Cyprus", "Czech Republic",
    "Denmark", "Estonia", "Finland", "France", "Georgia", "Germany", "Greece",
    "Hungary", "Iceland", "Ireland", "Italy", "Latvia", "Liechtenstein",
    "Lithuania", "Luxembourg", "Malta", "Republic of Moldova", "Monaco",
    "Montenegro", "Netherlands", "North Macedonia", "Norway", "Poland",
    "Portugal", "Romania", "San Marino", "Serbia", "Slovak Republic",
    "Slovenia", "Spain", "Sweden", "Switzerland", "Türkiye", "Ukraine",
    "United Kingdom",
]


def _stub(state: str) -> dict:
    return {
        "country": state,
        "police_cybercrime": {"name": "", "url": "", "phone": ""},
        "equality_body": {"name": "", "url": ""},
        "hotlines": [], "helplines": [], "report_urls": [],
        "verified": False,
    }


def cyprus_entry() -> dict:
    return {
        "country": "Cyprus",
        "police_cybercrime": {
            "name": "Cyprus Police - Office for Combating Cybercrime",
            "url": "https://www.police.gov.cy/police/police.nsf/dmlcybercrime_en/dmlcybercrime_en",
            "phone": "+357 22 808200",
        },
        "equality_body": {
            "name": "Commissioner for Administration and the Protection of Human Rights (Ombudsman) - Equality Body",
            "url": "http://www.ombudsman.gov.cy",
        },
        "hotlines": [
            {"name": "CYberSafety Hotline (illegal online content)",
             "url": "https://www.cybersafety.cy", "phone": "1480"},
        ],
        "helplines": [
            {"name": "European Child Helpline (Hope for Children)",
             "phone": "116 111", "audience": "children and teens"},
            {"name": "CYberSafety Helpline", "phone": "1480",
             "audience": "children, parents, educators"},
        ],
        "report_urls": ["https://www.cybersafety.cy/report"],
        "verified": True,
    }


def parse_equinet(html: str) -> dict[str, dict]:
    """Map state -> equality body {name, url} from the Equinet members page.

    Returns an empty dict if the page structure produces no recognisable matches
    (e.g. Cloudflare challenge page, markup changes) rather than crashing.
    """
    soup = BeautifulSoup(html, "lxml")
    found: dict[str, dict] = {}
    for a in soup.select("a"):
        text = " ".join(a.get_text(" ", strip=True).split())
        href = a.get("href") or ""
        for state in COE_STATES:
            if state.lower() in text.lower() and len(text) < 120 and "member" not in href:
                found.setdefault(state, {"name": text, "url": href})
    return found


def build(equinet_html: str | None) -> dict[str, dict]:
    registry = {s: _stub(s) for s in COE_STATES}
    if equinet_html:
        for state, body in parse_equinet(equinet_html).items():
            registry[state]["equality_body"] = body
    registry["Cyprus"] = cyprus_entry()
    return registry


def main() -> int:
    html = None
    try:
        html = httpx.get(EQUINET_URL, timeout=60, follow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0"}).text
        # Cloudflare or bot-challenge pages don't contain member links;
        # parse_equinet will return empty, which is handled gracefully.
    except httpx.HTTPError as exc:
        print(f"Equinet fetch failed ({exc}); writing stubs + Cyprus only")
    registry = build(html)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(registry, indent=2, ensure_ascii=False))
    filled = sum(1 for r in registry.values() if r["equality_body"]["name"])
    print(f"wrote {len(registry)} states ({filled} with equality body) -> {OUT}")

    # Data-quality sample for the 5 reference states
    sample_states = ["Germany", "France", "Greece", "Ireland", "Sweden"]
    print("\nEquality body sample (5 reference states):")
    for s in sample_states:
        name = registry[s]["equality_body"]["name"]
        print(f"  {s}: {name!r}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
