from pathlib import Path

from qdrant_client import QdrantClient

from app.ingestion import load_document_chunks
from app.retrieval_evaluation import (
    evaluate_retrieval,
    load_retrieval_cases,
)
from app.vector_store import VectorStore


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data"
CASES_PATH = (
    PROJECT_ROOT / "evaluation" / "retrieval_cases.json"
)


def main() -> None:
    chunks = load_document_chunks(DATA_ROOT)

    vector_store = VectorStore(
        client=QdrantClient(":memory:")
    )
    vector_store.index_chunks(chunks)

    cases = load_retrieval_cases(CASES_PATH)
    report = evaluate_retrieval(
        vector_store=vector_store,
        cases=cases,
        k=3,
    )

    print("Retrieval evaluation")
    print("--------------------")
    print(f"Cases: {report.case_count}")
    print(
        f"Top-1 accuracy: "
        f"{report.top_1_accuracy:.1%}"
    )
    print(
        f"Recall@3: "
        f"{report.recall_at_k:.1%}"
    )
    print(
        f"Product isolation: "
        f"{report.product_isolation_accuracy:.1%}"
    )
    print(
        f"Version isolation: "
        f"{report.version_isolation_accuracy:.1%}"
    )
    print(
        f"Average retrieval latency: "
        f"{report.average_latency_ms:.2f} ms"
    )

    if report.failed_case_ids:
        print(
            "Cases missing the expected section: "
            + ", ".join(report.failed_case_ids)
        )
    else:
        print("All expected sections were retrieved.")


if __name__ == "__main__":
    main()