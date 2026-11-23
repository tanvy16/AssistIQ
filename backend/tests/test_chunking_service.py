import pytest

from app.services.chunking_service import chunk_text, compute_content_hash, normalize_input


def test_normalize_input_collapses_whitespace():
    assert normalize_input("  Hello   world  ") == "Hello world"


def test_compute_content_hash_is_deterministic():
    content = "Reset corporate password using the self-service portal."
    assert compute_content_hash(content) == compute_content_hash(content)
    assert len(compute_content_hash(content)) == 64


def test_chunk_text_is_deterministic():
    text = (
        "Corporate password reset requires the self-service portal. "
        "Open the portal from the intranet homepage and choose Reset Password. "
        "Verify your identity with MFA before setting a new password."
    ) * 3
    first = chunk_text(text, chunk_size=120, chunk_overlap=20)
    second = chunk_text(text, chunk_size=120, chunk_overlap=20)
    assert [(c.chunk_index, c.content, c.content_hash) for c in first] == [
        (c.chunk_index, c.content, c.content_hash) for c in second
    ]


def test_chunk_text_applies_overlap():
    text = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu"
    chunks = chunk_text(text, chunk_size=20, chunk_overlap=8)
    assert len(chunks) >= 2
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1
    assert all(chunk.content for chunk in chunks)


def test_chunk_text_empty_input():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_text_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_text("content", chunk_size=0)
    with pytest.raises(ValueError):
        chunk_text("content", chunk_size=10, chunk_overlap=10)
