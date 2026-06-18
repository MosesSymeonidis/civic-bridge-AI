"""Parse the FSF hate-speech case database out of its Infogram embed.

Data source: https://e.infogram.com/a86ac286-44ad-48f0-ac73-f0488fa40539

The Infogram embed contains window.infographicData JSON (~155KB).  Case names
are stored in a map-chart entity where each row is:
  [country_name, count, group, coords, country_name, cases_newline_joined]

A separate bar-chart entity holds aggregate theme counts but does NOT map
individual cases to themes, so theme is left empty for Task 3 (HUDOC enrichment)
to fill in from the official HUDOC metadata.
"""
import json
import re
import sys
from pathlib import Path

import httpx

EMBED_URL = "https://e.infogram.com/a86ac286-44ad-48f0-ac73-f0488fa40539"
OUT = Path(__file__).resolve().parent.parent / "data" / "knowledge" / "cases.json"

# Country normalisation map: raw value in data -> canonical name
_COUNTRY_NORM: dict[str, str] = {
    "The Netherlands": "Netherlands",
    "Azerbajdsjan": "Azerbaijan",
}


def _extract_map_chart(data: dict) -> list[list]:
    """Return the rows from the geo-map chart entity (52 rows, 6 columns)."""
    entities: dict = data["elements"]["content"]["content"]["entities"]
    for entity in entities.values():
        if entity.get("type") != "CHART":
            continue
        cd = entity.get("props", {}).get("chartData", {})
        rows = cd.get("data", [[]])
        if not rows or not isinstance(rows[0], list):
            continue
        if len(rows[0]) >= 50:  # the map chart has 52 country rows
            # Verify it looks like the right chart (has geo coords in col 3)
            for row in rows[0]:
                if (
                    isinstance(row, list)
                    and len(row) >= 4
                    and isinstance(row[3], str)
                    and re.match(r"[\d.]+ [\d.]+", row[3])
                ):
                    return rows[0]
    return []


def _clean_country(raw: str) -> str:
    raw = raw.strip()
    return _COUNTRY_NORM.get(raw, raw)


def parse_infogram(html: str) -> list[dict]:
    """Parse case entries from the Infogram embed HTML.

    Returns a list of dicts, each with keys:
        name, theme, country, appno, date, conclusion, summary, hudoc_match
    """
    m = re.search(
        r"window\.infographicData\s*=\s*(\{.*?\});</script>", html, re.S
    )
    if not m:
        m = re.search(r"window\.infographicData=(\{.*?\});", html, re.S)
    if not m:
        raise ValueError("window.infographicData not found in HTML")

    data = json.loads(m.group(1))
    map_rows = _extract_map_chart(data)
    if not map_rows:
        raise ValueError(
            "map-chart entity not found; the Infogram embed structure changed"
        )

    cases: list[dict] = []
    seen: set[str] = set()

    for row in map_rows:
        # Row structure: [country, count, group, coords, country, cases_str]
        # Some rows have no cases (count is '' or 0)
        if len(row) < 6:
            continue
        country_raw = row[0] if isinstance(row[0], str) else ""
        cases_cell = row[5] if isinstance(row[5], str) else ""
        if not cases_cell.strip():
            continue

        country = _clean_country(country_raw)
        for raw_name in cases_cell.split("\n"):
            name = re.sub(r"\s+", " ", raw_name).strip()
            if not name or name in seen:
                continue
            seen.add(name)
            cases.append(
                {
                    "name": name,
                    "theme": "",         # enriched by Task 3 via HUDOC
                    "country": country,
                    "appno": "",
                    "date": "",
                    "conclusion": "",
                    "summary": "",
                    "hudoc_match": "unenriched",
                }
            )

    return cases


def main() -> int:
    html = httpx.get(
        EMBED_URL,
        timeout=60,
        headers={"User-Agent": "Mozilla/5.0"},
        follow_redirects=True,
    ).text
    cases = parse_infogram(html)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(cases, indent=2, ensure_ascii=False))
    print(f"wrote {len(cases)} cases -> {OUT}")
    return 0 if len(cases) >= 40 else 1


if __name__ == "__main__":
    sys.exit(main())
