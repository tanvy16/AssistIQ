import pytest

from app.adapters.chroma import ChromaAdapter, ChromaAdapterError


@pytest.fixture
def chroma_adapter(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(tmp_path / "chroma"))
    from app.adapters.chroma import reset_chroma_adapter
    from app.core.config import get_settings

    get_settings.cache_clear()
    reset_chroma_adapter()
    yield ChromaAdapter()
    reset_chroma_adapter()
    get_settings.cache_clear()


def test_add_and_search_chunks(chroma_adapter):
    ids = ["doc1:0", "doc1:1"]
    embeddings = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
    ]
    documents = [
        "Reset your corporate password using the self-service portal.",
        "VPN troubleshooting for remote employees.",
    ]
    metadatas = [
        {"document_id": "doc1", "status": "published", "title": "Password Reset"},
        {"document_id": "doc1", "status": "published", "title": "VPN Guide"},
    ]
    chroma_adapter.add_chunks(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    hits = chroma_adapter.similarity_search(
        query_embedding=[1.0, 0.0, 0.0],
        top_k=2,
        where={"status": "published"},
    )
    assert len(hits) == 2
    assert hits[0]["chroma_id"] == "doc1:0"
    assert hits[0]["similarity_score"] == pytest.approx(1.0)
    assert "password" in hits[0]["content"].lower()


def test_delete_chunks(chroma_adapter):
    chroma_adapter.add_chunks(
        ids=["doc2:0"],
        embeddings=[[1.0, 0.0]],
        documents=["Archive me"],
        metadatas=[{"status": "published"}],
    )
    chroma_adapter.delete_chunks(["doc2:0"])
    hits = chroma_adapter.similarity_search(
        query_embedding=[1.0, 0.0],
        top_k=1,
    )
    assert hits == []


def test_metadata_filter_excludes_non_matching(chroma_adapter):
    chroma_adapter.add_chunks(
        ids=["doc3:0", "doc3:1"],
        embeddings=[[1.0, 0.0], [0.9, 0.1]],
        documents=["Published article", "Draft article"],
        metadatas=[
            {"status": "published"},
            {"status": "draft"},
        ],
    )
    hits = chroma_adapter.similarity_search(
        query_embedding=[1.0, 0.0],
        top_k=5,
        where={"status": "published"},
    )
    assert len(hits) == 1
    assert hits[0]["content"] == "Published article"


def test_chroma_adapter_error_is_sanitized(monkeypatch, tmp_path):
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(tmp_path / "chroma"))

    def broken_get_collection(self):
        raise OSError("permission denied: /secret/chroma/data")

    monkeypatch.setattr(
        "app.adapters.chroma.ChromaAdapter.get_collection",
        broken_get_collection,
    )

    from app.adapters.chroma import ChromaAdapter, reset_chroma_adapter
    from app.core.config import get_settings

    get_settings.cache_clear()
    reset_chroma_adapter()
    adapter = ChromaAdapter()
    with pytest.raises(ChromaAdapterError) as exc_info:
        adapter.add_chunks(
            ids=["x:0"],
            embeddings=[[1.0]],
            documents=["test"],
            metadatas=[{}],
        )
    assert "/secret/chroma" not in str(exc_info.value)
