from pathlib import Path
from time import perf_counter

from qdrant_client import QdrantClient

from app.ingestion import load_document_chunks
from app.retrieval_evaluation import (
    RetrievalEvaluationReport,
    evaluate_retrieval,
    load_retrieval_cases,
)
from app.vector_store import VectorStore


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data"

CASE_PATHS = [
    PROJECT_ROOT / "evaluation" / "retrieval_cases.json",
    PROJECT_ROOT
    / "evaluation"
    / "hard_retrieval_cases.json",
]

EMBEDDING_MODELS = [
    "sentence-transformers/all-MiniLM-L6-v2",
    "BAAI/bge-small-en-v1.5",
]


def load_all_cases():
    """Combine the baseline and challenge evaluation datasets."""

    cases = []

    for path in CASE_PATHS:
        cases.extend(load_retrieval_cases(path))

    return cases


def evaluate_model(
    model_name: str,
) -> tuple[RetrievalEvaluationReport, float]:
    """Index and evaluate the dataset with one embedding model."""

    client = QdrantClient(":memory:")

    vector_store = VectorStore(
        client=client,
        collection_name="documentation",
        embedding_model=model_name,
    )

    chunks = load_document_chunks(DATA_ROOT)

    indexing_started = perf_counter()
    vector_store.index_chunks(chunks)
    indexing_ms = (
        perf_counter() - indexing_started
    ) * 1000

    report = evaluate_retrieval(
        vector_store=vector_store,
        cases=load_all_cases(),
        k=3,
    )

    return report, indexing_ms


def print_result(
    model_name: str,
    report: RetrievalEvaluationReport,
    indexing_ms: float,
) -> None:
    print()
    print(model_name)
    print("-" * len(model_name))
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
    print(f"Indexing time: {indexing_ms:.2f} ms")
    print(
        f"Average retrieval latency: "
        f"{report.average_latency_ms:.2f} ms"
    )

    if report.failed_case_ids:
        print(
            "Failed cases: "
            + ", ".join(report.failed_case_ids)
        )
    else:
        print("Failed cases: none")


def main() -> None:
    print("Hugging Face embedding model comparison")
    print("=======================================")
    print("Evaluation cases: baseline + challenge")

    for model_name in EMBEDDING_MODELS:
        report, indexing_ms = evaluate_model(model_name)

        print_result(
            model_name=model_name,
            report=report,
            indexing_ms=indexing_ms,
        )


if __name__ == "__main__":
    main()