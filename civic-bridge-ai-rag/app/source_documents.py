"""Source document metadata shared by ingestion and retrieval.

The Chroma index stores a copy of this metadata on each chunk. Retrieval also
uses the doc_id mapping as a compatibility fallback for indexes built before
URL metadata was added.
"""

_REFERENCE_URL_OVERRIDES = {
    "https://www.coe.int/en/web/octopus/good-practices": (
        "https://www.coe.int/en/web/octopus/"
    ),
}


def normalize_reference_url(url: str) -> str:
    return _REFERENCE_URL_OVERRIDES.get(url, url)


SOURCE_DOCUMENTS = {
    "cmrec2022-16.pdf": {
        "doc_id": "cmrec2022-16",
        "title": "CM/Rec(2022)16 + Explanatory Memorandum",
        "url": "https://edoc.coe.int/en/racism/11119-combating-hate-speech-recommendation-cmrec202216-and-explanatory-memorandum.html",
    },
    "CETS_189.docx.pdf": {
        "doc_id": "cets189",
        "title": "Budapest Convention Additional Protocol (CETS 189)",
        "url": "https://www.coe.int/en/web/conventions/full-list?module=treaty-detail&treatynum=189",
    },
    "CETS_225_EN.docx.pdf": {
        "doc_id": "cets225",
        "title": "AI Framework Convention (CETS 225)",
        "url": "https://www.coe.int/en/web/conventions/full-list?module=treaty-detail&treatynum=225",
    },
    "ECHR Art. 10.pdf": {
        "doc_id": "echr-art10-guide",
        "title": "Guide on ECHR Article 10",
        "url": "https://ks.echr.coe.int/documents/d/echr-ks/guide_art_10_eng",
    },
    "ECRI Annual report 2025.pdf": {
        "doc_id": "ecri-2025",
        "title": "ECRI Annual Report 2025",
        "url": "https://www.coe.int/en/web/european-commission-against-racism-and-intolerance/annual-reports",
    },
    "PREMS 099126 GBR 1270 Rapport SG 2026 WEB A4 2756-4240-7700.1.pdf": {
        "doc_id": "sg-2026",
        "title": "Secretary General Report 2026: New Democratic Pact",
        "url": "https://www.coe.int/en/web/secretary-general/reports",
    },
    "2542_57_XR Good practice study_PROV.pdf": {
        "doc_id": "octopus-gps",
        "title": "Octopus Good Practice Study (Protocol on Xenophobia and Racism)",
        "url": "https://www.coe.int/en/web/octopus/",
    },
}

SOURCE_URLS_BY_DOC_ID = {
    doc["doc_id"]: doc["url"] for doc in SOURCE_DOCUMENTS.values()
}
