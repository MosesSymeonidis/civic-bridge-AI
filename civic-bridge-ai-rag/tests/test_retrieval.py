import app.retrieval as retrieval


def test_search_formats_hits(monkeypatch):
    class FakeCol:
        def query(self, query_embeddings, n_results):
            return {
                "documents": [["chunk text one", "chunk text two"]],
                "metadatas": [[{"doc_id": "ecri-2025", "title": "ECRI Annual Report 2025", "page": 12,
                                "url": "https://example.org/ecri-2025"},
                               {"doc_id": "sg-2026", "title": "SG Report 2026", "page": 3}]],
            }
    monkeypatch.setattr(retrieval, "_collection", lambda: FakeCol())
    monkeypatch.setattr(retrieval.llm, "embed", lambda texts: [[0.0] * 8])
    hits = retrieval.search("what does ECRI say", k=2)
    assert hits[0]["source"] == "ECRI Annual Report 2025"
    assert hits[0]["page"] == 12
    assert hits[0]["url"] == "https://example.org/ecri-2025"


def test_search_adds_source_url_from_doc_id_when_index_metadata_is_old(monkeypatch):
    class FakeCol:
        def query(self, query_embeddings, n_results):
            return {
                "documents": [["chunk text"]],
                "metadatas": [[{"doc_id": "cets189", "title": "CETS 189", "page": 2}]],
            }

    monkeypatch.setattr(retrieval, "_collection", lambda: FakeCol())
    monkeypatch.setattr(retrieval.llm, "embed", lambda texts: [[0.0] * 8])
    hits = retrieval.search("xenophobia protocol", k=1)
    assert hits[0]["url"].startswith("https://")


def test_search_rewrites_stale_octopus_source_url(monkeypatch):
    class FakeCol:
        def query(self, query_embeddings, n_results):
            return {
                "documents": [["chunk text"]],
                "metadatas": [[{
                    "doc_id": "octopus-gps",
                    "title": "Octopus Good Practice Study",
                    "page": 4,
                    "url": "https://www.coe.int/en/web/octopus/good-practices",
                }]],
            }

    monkeypatch.setattr(retrieval, "_collection", lambda: FakeCol())
    monkeypatch.setattr(retrieval.llm, "embed", lambda texts: [[0.0] * 8])

    hits = retrieval.search("good practices", k=1)

    assert hits[0]["url"] == "https://www.coe.int/en/web/octopus/"


def test_context_block_numbers_sources():
    hits = [{"text": "abc", "source": "ECRI Annual Report 2025", "page": 12}]
    block = retrieval.context_block(hits)
    assert "[S1] ECRI Annual Report 2025, p.12" in block


def test_search_degrades_when_index_missing(monkeypatch):
    def boom():
        raise RuntimeError("no index")
    monkeypatch.setattr(retrieval, "_collection", boom)
    assert retrieval.search("anything") == []
