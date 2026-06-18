"""Live rehearsal: run the golden set through the real classifier and report.

Usage: .venv/bin/python rehearse.py    (requires API keys; costs a few cents)
"""
import json
import sys
from pathlib import Path

from app import stats
from app.classify import analyze

GOLDEN = Path("tests/golden_set.jsonl")


def main() -> int:
    failures = 0
    for line in GOLDEN.read_text().splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        try:
            r = analyze(e["text"], country="Cyprus", age_band="18+")
        except Exception as exc:
            print(f"{e['id']}: ERROR {exc}")
            failures += 1
            continue
        # Feed the awareness dashboard with real classifier output (categorical
        # signals only), so a rehearsal run doubles as demo data.
        stats.record(tier=r.tier, barriers=[b.id for b in r.barriers],
                     themes=r.themes, country="Cyprus", role="teacher",
                     age_band="18+")
        tier_ok = e["tier_min"] <= r.tier <= e["tier_max"]
        found = {b.id for b in r.barriers}
        barriers_ok = set(e["barriers"]) <= found if e["barriers"] else True
        status = "OK " if (tier_ok and barriers_ok) else "FAIL"
        if status == "FAIL":
            failures += 1
        print(f"{e['id']} {status} tier={r.tier} (want {e['tier_min']}-{e['tier_max']}) "
              f"barriers={sorted(found)} (want {e['barriers']})")
    print(f"\n{failures} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
