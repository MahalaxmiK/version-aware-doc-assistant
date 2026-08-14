import json
from pathlib import Path

import pytest
from qdrant_client import QdrantClient

from app.ingestion import load_document_chunks
from app.retrieval_evaluation import (
    RetrievalCase,
    evaluate_retrieval,
    load_retrieval_cases,
)
from app.vector_store import VectorStore


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data"
CASES_PATH = (
    PROJECT_ROOT / "evaluation" / "retrieval_cases.json"
)


@pytest.fixture(scope="module")
def evaluated_vector_store() -> VectorStore:
    client = QdrantClient(":memory:")
    store = VectorStore(client=client)
    store.index_chunks(load_document_chunks(DATA_ROOT))
    return store


def test_loads_labeled_retrieval_cases() -> None:
    cases = load_retrieval_cases(CASES_PATH)

    assert len(cases) == 12
    assert {
        case.product for case in cases
    } == {
        "examplecloud",
        "paymentcloud",
        "supportdesk",
    }
    assert all(case.expected_section for case in cases)


def test_evaluation_meets_retrieval_baseline(
    evaluated_vector_store: VectorStore,
) -> None:
    cases = load_retrieval_cases(CASES_PATH)

    report = evaluate_retrieval(
        vector_store=evaluated_vector_store,
        cases=cases,
        k=3,
    )

    assert report.case_count == 12
    assert report.top_1_accuracy >= 0.90
    assert report.recall_at_k == 1.0
    assert report.product_isolation_accuracy == 1.0
    assert report.version_isolation_accuracy == 1.0
    assert report.failed_case_ids == []
    assert report.average_latency_ms >= 0


def test_rejects_empty_evaluation_case_list(
    evaluated_vector_store: VectorStore,
) -> None:
    with pytest.raises(
        ValueError,
        match="At least one retrieval case is required",
    ):
        evaluate_retrieval(
            vector_store=evaluated_vector_store,
            cases=[],
        )


def test_rejects_invalid_k(
    evaluated_vector_store: VectorStore,
) -> None:
    case = RetrievalCase(
        case_id="valid-case",
        query="How do I authenticate?",
        product="examplecloud",
        version="v1",
        expected_section="Authentication",
    )

    with pytest.raises(
        ValueError,
        match="k must be at least 1",
    ):
        evaluate_retrieval(
            vector_store=evaluated_vector_store,
            cases=[case],
            k=0,
        )


def test_rejects_case_with_missing_fields(
    tmp_path: Path,
) -> None:
    invalid_path = tmp_path / "invalid-cases.json"
    invalid_path.write_text(
        json.dumps(
            [
                {
                    "id": "missing-version",
                    "query": "How do I authenticate?",
                    "product": "examplecloud",
                    "expected_section": "Authentication",
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="missing fields: version",
    ):
        load_retrieval_cases(invalid_path)