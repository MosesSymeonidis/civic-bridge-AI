"""Download CM/Rec(2022)16 and its Explanatory Memorandum into data/raw/legal/.

The PREMS 083822 booklet contains both the Recommendation and the Explanatory
Memorandum in one PDF. URLs on coe.int move; we try candidates and verify by
content keywords. On total failure we print manual instructions and exit 1.
"""
import sys
from pathlib import Path

import httpx
from pypdf import PdfReader

OUT = Path(__file__).resolve().parent.parent / "data" / "raw" / "legal"

# Ordered by preference: try confirmed-working URLs first.
# edoc.coe.int is the Council of Europe's official publication catalogue and
# provides a stable, Cloudflare-free download endpoint.
CANDIDATES = [
    # edoc.coe.int - PREMS 083822 booklet: Recommendation + Explanatory Memorandum
    # 49 pages, 1 MB, confirmed working 2026-06-11
    "https://edoc.coe.int/en/module/ec_addformat/download?cle=e2d56b6b53ce40332aec920b78d030c1&k=afe9f0c49794d70aef7eedf970c30e04",
    # rm.coe.int PREMS 083822 booklet (may return 403 from automated clients)
    "https://rm.coe.int/prems-083822-gbr-2018-recommendation-on-combating-hate-speech-memorand/1680a710c9",
    # rm.coe.int direct hash
    "https://rm.coe.int/1680a710c9",
]
KEYWORDS = ["CM/Rec(2022)16", "hate speech"]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,*/*;q=0.9",
    "Referer": "https://edoc.coe.int/en/racism/11119-combating-hate-speech-recommendation-cmrec202216-and-explanatory-memorandum.html",
}


def fetch(url: str) -> bytes | None:
    try:
        r = httpx.get(url, follow_redirects=True, timeout=60, headers=_HEADERS)
        r.raise_for_status()
        return r.content
    except httpx.HTTPError as exc:
        print(f"  failed: {url} ({exc})")
        return None


def looks_right(pdf_path: Path) -> bool:
    try:
        reader = PdfReader(str(pdf_path))
        text = "".join((p.extract_text() or "") for p in reader.pages[:5])
        return all(k.lower() in text.lower() for k in KEYWORDS)
    except Exception:
        return False


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "cmrec2022-16.pdf"
    if target.exists() and looks_right(target):
        print(f"already present: {target}")
        return 0
    for url in CANDIDATES:
        print(f"  trying: {url}")
        content = fetch(url)
        if content and content[:4] == b"%PDF":
            target.write_bytes(content)
            if looks_right(target):
                print(f"saved: {target}")
                return 0
            print("  downloaded but keyword check failed, discarding")
            target.unlink(missing_ok=True)
        elif content:
            print(f"  not a PDF (starts with: {content[:20]!r})")
    print(
        "Could not auto-download. Manually download the PREMS 083822 booklet\n"
        "'Combating Hate Speech: Recommendation CM/Rec(2022)16 and explanatory\n"
        f"memorandum' from coe.int and save it as {target}"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
