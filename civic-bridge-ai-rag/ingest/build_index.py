"""Extract text from every PDF in data/raw/legal/, chunk, embed, store in chroma."""
import sys
from pathlib import Path

import chromadb
from pypdf import PdfReader

from app import config
from app.llm import embed
from app.source_documents import SOURCE_DOCUMENTS

DOCS = SOURCE_DOCUMENTS


def chunk_pages(pages, doc_id: str, title: str,
                url: str | None = None,
                size: int = 3200, overlap: int = 400) -> list[dict]:
    if overlap >= size:
        raise ValueError(f"overlap ({overlap}) must be smaller than size ({size})")
    chunks = []
    for page_no, text in pages:
        text = " ".join(text.split())
        if not text:
            continue
        start = 0
        while start < len(text):
            piece = text[start:start + size]
            chunks.append({
                "id": f"{doc_id}-p{page_no}-c{start}",
                "text": piece,
                "meta": {"doc_id": doc_id, "title": title, "page": page_no,
                         "url": url or ""},
            })
            if start + size >= len(text):
                break
            start += size - overlap
    return chunks


def main() -> int:
    legal = config.RAW / "legal"
    client = chromadb.PersistentClient(path=config.CHROMA_PATH)
    col = client.get_or_create_collection("legal_corpus")
    total = 0
    for filename, doc in DOCS.items():
        doc_id = doc["doc_id"]
        title = doc["title"]
        path = legal / filename
        if not path.exists():
            print(f"  MISSING: {filename} (skipped)")
            continue
        reader = PdfReader(str(path))
        pages = [(i + 1, p.extract_text() or "") for i, p in enumerate(reader.pages)]
        chunks = chunk_pages(pages, doc_id, title, url=doc["url"])
        for i in range(0, len(chunks), 64):
            batch = chunks[i:i + 64]
            col.upsert(
                ids=[c["id"] for c in batch],
                documents=[c["text"] for c in batch],
                embeddings=embed([c["text"] for c in batch]),
                metadatas=[c["meta"] for c in batch],
            )
        total += len(chunks)
        print(f"  {doc_id}: {len(chunks)} chunks")
    print(f"indexed {total} chunks -> {config.CHROMA_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
