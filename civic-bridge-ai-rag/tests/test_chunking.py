from ingest.build_index import chunk_pages


def test_chunk_pages_splits_and_overlaps():
    pages = [(1, "A" * 5000), (2, "B" * 1000)]
    chunks = chunk_pages(pages, doc_id="test", title="Test Doc",
                         url="https://example.org/test-doc",
                         size=3200, overlap=400)
    assert all(len(c["text"]) <= 3200 for c in chunks)
    assert chunks[0]["meta"]["doc_id"] == "test"
    assert chunks[0]["meta"]["page"] == 1
    assert chunks[0]["meta"]["url"] == "https://example.org/test-doc"
    # overlap: second chunk of page 1 starts inside the first
    assert chunks[1]["text"][:400] == chunks[0]["text"][-400:]


def test_chunk_skips_empty_pages():
    assert chunk_pages([(1, "   ")], doc_id="x", title="x") == []


def test_chunk_rejects_overlap_ge_size():
    import pytest
    with pytest.raises(ValueError):
        chunk_pages([(1, "x" * 100)], doc_id="d", title="t", size=50, overlap=60)
