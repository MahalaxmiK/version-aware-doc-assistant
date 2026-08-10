from pathlib import Path

from app.ingestion import load_document_chunks


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data"


def test_loads_all_versioned_sections() -> None:
    chunks = load_document_chunks(DATA_ROOT)

    assert len(chunks) == 6

    versions = {chunk.version for chunk in chunks}
    assert versions == {"v1", "v2"}

    assert all(chunk.product == "examplecloud" for chunk in chunks)
    assert all(chunk.text for chunk in chunks)


def test_preserves_version_specific_rate_limits() -> None:
    chunks = load_document_chunks(DATA_ROOT)

    v1_rate_limit = next(
        chunk
        for chunk in chunks
        if chunk.version == "v1"
        and chunk.section == "Request limits"
    )

    v2_rate_limit = next(
        chunk
        for chunk in chunks
        if chunk.version == "v2"
        and chunk.section == "Request limits"
    )

    assert "100 API requests per minute" in v1_rate_limit.text
    assert "250 API requests per minute" in v2_rate_limit.text


def test_creates_unique_chunk_ids() -> None:
    chunks = load_document_chunks(DATA_ROOT)

    assert chunks

    chunk_ids = [chunk.chunk_id for chunk in chunks]

    assert len(chunk_ids) == len(set(chunk_ids))


def test_records_source_metadata() -> None:
    chunks = load_document_chunks(DATA_ROOT)

    assert any(
        chunk.source == "examplecloud/v1/api-guide.md"
        for chunk in chunks
    )

    assert any(
        chunk.source == "examplecloud/v2/api-guide.md"
        for chunk in chunks
    )