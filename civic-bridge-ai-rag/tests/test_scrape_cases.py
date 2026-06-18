from pathlib import Path

from ingest.scrape_cases import parse_infogram

FIXTURE = Path(__file__).parent / "fixtures" / "infogram.html"


def test_parse_infogram_extracts_cases():
    cases = parse_infogram(FIXTURE.read_text())
    assert len(cases) >= 40
    assert len(cases) == 58  # frozen fixture; update if the source grows
    sample = cases[0]
    assert set(sample) >= {"name", "theme", "country"}
    names = [c["name"] for c in cases]
    assert any("v." in n or " v " in n for n in names)
