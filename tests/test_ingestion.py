from pathlib import Path

from app.ingestion import load_document_chunks


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data"


def test_loads_all_versioned_sections() -> None:
    chunks = load_document_chunks(DATA_ROOT)

    assert len(chunks) == 18

    products = {chunk.product for chunk in chunks}
    versions = {chunk.version for chunk in chunks}

    assert products == {
        "examplecloud",
        "paymentcloud",
        "supportdesk",
    }
    assert versions == {"v1", "v2"}
    assert all(chunk.text for chunk in chunks)


def test_preserves_examplecloud_version_specific_rate_limits() -> None:
    chunks = load_document_chunks(DATA_ROOT)

    v1_rate_limit = next(
        chunk
        for chunk in chunks
        if chunk.product == "examplecloud"
        and chunk.version == "v1"
        and chunk.section == "Request limits"
    )

    v2_rate_limit = next(
        chunk
        for chunk in chunks
        if chunk.product == "examplecloud"
        and chunk.version == "v2"
        and chunk.section == "Request limits"
    )

    assert "100 API requests per minute" in v1_rate_limit.text
    assert "250 API requests per minute" in v2_rate_limit.text


def test_preserves_paymentcloud_version_specific_refund_rules() -> None:
    chunks = load_document_chunks(DATA_ROOT)

    v1_refunds = next(
        chunk
        for chunk in chunks
        if chunk.product == "paymentcloud"
        and chunk.version == "v1"
        and chunk.section == "Refunds"
    )

    v2_refunds = next(
        chunk
        for chunk in chunks
        if chunk.product == "paymentcloud"
        and chunk.version == "v2"
        and chunk.section == "Refunds"
    )

    assert "full refunds only" in v1_refunds.text
    assert "full and partial refunds" in v2_refunds.text


def test_preserves_supportdesk_version_specific_retention_rules() -> None:
    chunks = load_document_chunks(DATA_ROOT)

    v1_retention = next(
        chunk
        for chunk in chunks
        if chunk.product == "supportdesk"
        and chunk.version == "v1"
        and chunk.section == "Ticket retention"
    )

    v2_retention = next(
        chunk
        for chunk in chunks
        if chunk.product == "supportdesk"
        and chunk.version == "v2"
        and chunk.section == "Ticket retention"
    )

    assert "90 days" in v1_retention.text
    assert "365 days" in v2_retention.text


def test_creates_unique_chunk_ids() -> None:
    chunks = load_document_chunks(DATA_ROOT)

    assert chunks

    chunk_ids = [chunk.chunk_id for chunk in chunks]

    assert len(chunk_ids) == len(set(chunk_ids))


def test_records_source_metadata() -> None:
    chunks = load_document_chunks(DATA_ROOT)

    expected_sources = {
        "examplecloud/v1/api-guide.md",
        "examplecloud/v2/api-guide.md",
        "paymentcloud/v1/api-guide.md",
        "paymentcloud/v2/api-guide.md",
        "supportdesk/v1/api-guide.md",
        "supportdesk/v2/api-guide.md",
    }

    actual_sources = {chunk.source for chunk in chunks}

    assert expected_sources.issubset(actual_sources)