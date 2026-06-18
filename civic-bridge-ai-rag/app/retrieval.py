import logging

import functools

import chromadb

from app import config, llm
from app.source_documents import SOURCE_URLS_BY_DOC_ID, normalize_reference_url

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def _collection():
    client = chromadb.PersistentClient(path=config.CHROMA_PATH)
    return client.get_collection("legal_corpus")


def search(query: str, k: int = 4) -> list[dict]:
    try:
        col = _collection()
        res = col.query(query_embeddings=[llm.embed([query])[0]], n_results=k)
    except Exception as exc:
        logger.warning("retrieval failed, falling back to norms-core-only: %s", exc)
        return []  # degraded mode: chat falls back to norms-core-only with a notice
    hits = []
    for text, meta in zip(res["documents"][0], res["metadatas"][0]):
        url = normalize_reference_url(
            meta.get("url") or SOURCE_URLS_BY_DOC_ID.get(meta.get("doc_id"), "")
        )
        hits.append({"text": text, "source": meta["title"], "page": meta["page"],
                     "url": url})
    return hits


def context_block(hits: list[dict]) -> str:
    return "\n".join(
        f'[S{i + 1}] {h["source"]}, p.{h["page"]}: {h["text"]}'
        for i, h in enumerate(hits)
    )
