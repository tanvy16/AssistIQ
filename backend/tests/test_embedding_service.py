from app.services.embedding_service import HashEmbeddingService, normalize_text


def test_embed_query_returns_normalized_vector():
    service = HashEmbeddingService()
    vector = service.embed_query("reset corporate password")
    assert len(vector) == service.dimension
    assert abs(sum(v * v for v in vector) - 1.0) < 1e-6


def test_embed_documents_batch_matches_single():
    service = HashEmbeddingService()
    texts = ["password reset guide", "vpn troubleshooting"]
    batch = service.embed_documents(texts)
    assert len(batch) == 2
    assert batch[0] == service.embed_query(texts[0])


def test_similar_texts_have_higher_similarity():
    service = HashEmbeddingService()
    query = service.embed_query("corporate password reset portal")
    doc_close = service.embed_query("reset corporate password via portal")
    doc_far = service.embed_query("install printer driver on Windows")
    close_score = sum(a * b for a, b in zip(query, doc_close))
    far_score = sum(a * b for a, b in zip(query, doc_far))
    assert close_score > far_score


def test_normalize_text_matches_chunking_normalization():
    assert normalize_text("  PASSWORD Reset  ") == "password reset"
