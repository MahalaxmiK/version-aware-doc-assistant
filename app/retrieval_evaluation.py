import json
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from app.vector_store import VectorStore


@dataclass(frozen=True)
class RetrievalCase:
    """A labeled question with its expected retrieval target."""

    case_id: str
    query: str
    product: str
    version: str
    expected_section: str


@dataclass(frozen=True)
class RetrievalCaseResult:
    """The measured retrieval behavior for one evaluation case."""

    case: RetrievalCase
    retrieved_sections: list[str]
    top_score: float | None
    top_1_hit: bool
    recall_at_k_hit: bool
    product_isolated: bool
    version_isolated: bool
    latency_ms: float


@dataclass(frozen=True)
class RetrievalEvaluationReport:
    """Aggregated retrieval metrics across all evaluation cases."""

    case_count: int
    top_1_accuracy: float
    recall_at_k: float
    product_isolation_accuracy: float
    version_isolation_accuracy: float
    average_latency_ms: float
    failed_case_ids: list[str]


def load_retrieval_cases(path: Path) -> list[RetrievalCase]:
    """Load and validate labeled retrieval cases from JSON."""

    raw_cases = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError(
            "Retrieval evaluation data must be a non-empty list"
        )

    cases: list[RetrievalCase] = []

    for raw_case in raw_cases:
        required_fields = {
            "id",
            "query",
            "product",
            "version",
            "expected_section",
        }

        missing_fields = required_fields - raw_case.keys()

        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise ValueError(
                f"Retrieval case is missing fields: {missing}"
            )

        case = RetrievalCase(
            case_id=str(raw_case["id"]).strip(),
            query=str(raw_case["query"]).strip(),
            product=str(raw_case["product"]).strip(),
            version=str(raw_case["version"]).strip(),
            expected_section=str(
                raw_case["expected_section"]
            ).strip(),
        )

        if not all(
            [
                case.case_id,
                case.query,
                case.product,
                case.version,
                case.expected_section,
            ]
        ):
            raise ValueError(
                "Retrieval case fields cannot be empty"
            )

        cases.append(case)

    return cases


def evaluate_retrieval(
    vector_store: VectorStore,
    cases: list[RetrievalCase],
    k: int = 3,
) -> RetrievalEvaluationReport:
    """Run labeled cases and calculate retrieval quality metrics."""

    if not cases:
        raise ValueError("At least one retrieval case is required")

    if k < 1:
        raise ValueError("k must be at least 1")

    results: list[RetrievalCaseResult] = []

    for case in cases:
        started_at = perf_counter()

        retrieved = vector_store.search(
            query=case.query,
            product=case.product,
            version=case.version,
            limit=k,
        )

        latency_ms = (perf_counter() - started_at) * 1000
        retrieved_sections = [
            result.chunk.section for result in retrieved
        ]

        top_1_hit = bool(
            retrieved_sections
            and retrieved_sections[0] == case.expected_section
        )

        recall_at_k_hit = (
            case.expected_section in retrieved_sections
        )

        product_isolated = bool(retrieved) and all(
            result.chunk.product == case.product
            for result in retrieved
        )

        version_isolated = bool(retrieved) and all(
            result.chunk.version == case.version
            for result in retrieved
        )

        results.append(
            RetrievalCaseResult(
                case=case,
                retrieved_sections=retrieved_sections,
                top_score=(
                    retrieved[0].score if retrieved else None
                ),
                top_1_hit=top_1_hit,
                recall_at_k_hit=recall_at_k_hit,
                product_isolated=product_isolated,
                version_isolated=version_isolated,
                latency_ms=latency_ms,
            )
        )

    case_count = len(results)

    return RetrievalEvaluationReport(
        case_count=case_count,
        top_1_accuracy=sum(
            result.top_1_hit for result in results
        )
        / case_count,
        recall_at_k=sum(
            result.recall_at_k_hit for result in results
        )
        / case_count,
        product_isolation_accuracy=sum(
            result.product_isolated for result in results
        )
        / case_count,
        version_isolation_accuracy=sum(
            result.version_isolated for result in results
        )
        / case_count,
        average_latency_ms=sum(
            result.latency_ms for result in results
        )
        / case_count,
        failed_case_ids=[
            result.case.case_id
            for result in results
            if not result.recall_at_k_hit
        ],
    )