from pathlib import Path

import pytest
from qdrant_client import QdrantClient

from app.ingestion import load_document_chunks
from app.vector_store import VectorStore


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data"


@pytest.fixture(scope="module")
def vector_store() -> VectorStore:
    """Create and populate an isolated in-memory vector store."""

    client = QdrantClient(":memory:")
    store = VectorStore(client=client)

    chunks = load_document_chunks(DATA_ROOT)
    store.index_chunks(chunks)

    return store


def test_indexes_all_chunks(
    vector_store: VectorStore,
) -> None:
    collection = vector_store.client.get_collection(
        vector_store.collection_name
    )

    assert collection.points_count == 6


def test_retrieves_authentication_by_meaning(
    vector_store: VectorStore,
) -> None:
    results = vector_store.search(
        query="What credentials should a client send?",
        product="examplecloud",
        version="v2",
        limit=1,
    )

    assert len(results) == 1
    assert results[0].chunk.section == "Authentication"
    assert "OAuth 2.0" in results[0].chunk.text


def test_retrieves_rate_limit_by_meaning(
    vector_store: VectorStore,
) -> None:
    results = vector_store.search(
        query="What happens if I send too many requests?",
        product="examplecloud",
        version="v1",
        limit=1,
    )

    assert len(results) == 1
    assert results[0].chunk.section == "Request limits"
    assert "100 API requests per minute" in results[0].chunk.text
    assert "429" in results[0].chunk.text


def test_filters_results_by_version(
    vector_store: VectorStore,
) -> None:
    v1_results = vector_store.search(
        query="What is the request limit?",
        product="examplecloud",
        version="v1",
        limit=3,
    )

    v2_results = vector_store.search(
        query="What is the request limit?",
        product="examplecloud",
        version="v2",
        limit=3,
    )

    assert v1_results
    assert v2_results

    assert all(
        result.chunk.version == "v1"
        for result in v1_results
    )

    assert all(
        result.chunk.version == "v2"
        for result in v2_results
    )

    assert any(
        "100 API requests per minute" in result.chunk.text
        for result in v1_results
    )

    assert any(
        "250 API requests per minute" in result.chunk.text
        for result in v2_results
    )


def test_filters_results_by_product(
    vector_store: VectorStore,
) -> None:
    results = vector_store.search(
        query="How do I authenticate?",
        product="unknown-product",
        version="v2",
    )

    assert results == []


def test_preserves_source_metadata(
    vector_store: VectorStore,
) -> None:
    results = vector_store.search(
        query="Which export formats are supported?",
        product="examplecloud",
        version="v2",
        limit=1,
    )

    assert len(results) == 1
    assert results[0].chunk.section == "Data export"
    assert (
        results[0].chunk.source
        == "examplecloud/v2/api-guide.md"
    )


@pytest.mark.parametrize(
    ("query", "product", "version", "limit"),
    [
        ("", "examplecloud", "v1", 1),
        ("How do I authenticate?", "", "v1", 1),
        ("How do I authenticate?", "examplecloud", "", 1),
        ("How do I authenticate?", "examplecloud", "v1", 0),
    ],
)
def test_rejects_invalid_search_inputs(
    vector_store: VectorStore,
    query: str,
    product: str,
    version: str,
    limit: int,
) -> None:
    with pytest.raises(ValueError):
        vector_store.search(
            query=query,
            product=product,
            version=version,
            limit=limit,
        )