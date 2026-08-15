import json
from dataclasses import dataclass
from pathlib import Path

from app.agent_models import AgentAction
from app.agent_router import AgentRouter
from app.agent_service import AgentResponse, AgentService
from app.rag_service import (
    ABSTENTION_MESSAGE,
    Citation,
    RAGResponse,
)


AVAILABLE_VERSIONS = {
    "examplecloud": ("v1", "v2"),
    "paymentcloud": ("v1", "v2"),
    "supportdesk": ("v1", "v2"),
}


@dataclass(frozen=True)
class AgentEvaluationCase:
    """One labeled bounded-agent workflow case."""

    case_id: str
    question: str
    product: str
    requested_versions: tuple[str, ...]
    comparison_requested: bool
    rag_outcome: str
    expected_action: str
    expected_versions: tuple[str, ...]
    expected_answered: bool | None
    expect_citations: bool


@dataclass(frozen=True)
class AgentCaseResult:
    """Measured outcome for one behavioral case."""

    case_id: str
    passed: bool
    routing_correct: bool
    abstention_correct: bool | None
    citations_correct: bool | None
    scope_correct: bool | None


@dataclass(frozen=True)
class AgentEvaluationReport:
    """Aggregate agent workflow evaluation metrics."""

    case_count: int
    passed_count: int
    workflow_accuracy: float
    routing_accuracy: float
    abstention_accuracy: float
    citation_accuracy: float
    scope_accuracy: float
    failed_case_ids: list[str]


class EvaluationRAGService:
    """Controlled RAG test double for workflow evaluation."""

    def __init__(
        self,
        outcomes: dict[tuple[str, str], str],
    ) -> None:
        self.outcomes = outcomes

    def answer(
        self,
        question: str,
        product: str,
        version: str,
    ) -> RAGResponse:
        outcome = self.outcomes.get(
            (question, product),
            "grounded",
        )

        if outcome == "abstain":
            return RAGResponse(
                answered=False,
                answer=ABSTENTION_MESSAGE,
                citations=(),
                evidence=(),
            )

        citation = Citation(
            evidence_id="E1",
            product=product,
            version=version,
            source=f"{product}/{version}/evaluation.md",
            title=f"{product} evaluation document",
            section="Evaluation section",
        )

        return RAGResponse(
            answered=True,
            answer=(
                f"Grounded evaluation answer for "
                f"{product} {version}."
            ),
            citations=(citation,),
            evidence=(),
        )


def load_agent_cases(
    path: Path,
) -> list[AgentEvaluationCase]:
    """Load labeled agent workflow cases."""

    raw_cases = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError(
            "Agent evaluation data must be a non-empty list"
        )

    cases = []

    for item in raw_cases:
        cases.append(
            AgentEvaluationCase(
                case_id=str(item["id"]),
                question=str(item["question"]),
                product=str(item["product"]),
                requested_versions=tuple(
                    item["requested_versions"]
                ),
                comparison_requested=bool(
                    item["comparison_requested"]
                ),
                rag_outcome=str(item["rag_outcome"]),
                expected_action=str(item["expected_action"]),
                expected_versions=tuple(
                    item["expected_versions"]
                ),
                expected_answered=item["expected_answered"],
                expect_citations=bool(
                    item["expect_citations"]
                ),
            )
        )

    return cases


def evaluate_agent_cases(
    cases: list[AgentEvaluationCase],
) -> AgentEvaluationReport:
    """Evaluate bounded routing, abstention, and citations."""

    if not cases:
        raise ValueError(
            "At least one agent evaluation case is required"
        )

    outcomes = {
        (case.question, case.product): case.rag_outcome
        for case in cases
    }

    service = AgentService(
        router=AgentRouter(
            available_versions=AVAILABLE_VERSIONS
        ),
        rag_service=EvaluationRAGService(outcomes),
    )

    results = [
        _evaluate_case(service, case)
        for case in cases
    ]

    abstention_results = [
        result.abstention_correct
        for result in results
        if result.abstention_correct is not None
    ]

    citation_results = [
        result.citations_correct
        for result in results
        if result.citations_correct is not None
    ]

    scope_results = [
        result.scope_correct
        for result in results
        if result.scope_correct is not None
    ]

    return AgentEvaluationReport(
        case_count=len(results),
        passed_count=sum(
            result.passed for result in results
        ),
        workflow_accuracy=_accuracy(
            [result.passed for result in results]
        ),
        routing_accuracy=_accuracy(
            [
                result.routing_correct
                for result in results
            ]
        ),
        abstention_accuracy=_accuracy(
            abstention_results
        ),
        citation_accuracy=_accuracy(
            citation_results
        ),
        scope_accuracy=_accuracy(scope_results),
        failed_case_ids=[
            result.case_id
            for result in results
            if not result.passed
        ],
    )


def _evaluate_case(
    service: AgentService,
    case: AgentEvaluationCase,
) -> AgentCaseResult:
    try:
        response = service.run(
            question=case.question,
            product=case.product,
            requested_versions=case.requested_versions,
            comparison_requested=(
                case.comparison_requested
            ),
        )
    except ValueError:
        rejected_correctly = (
            case.expected_action == "reject"
        )

        return AgentCaseResult(
            case_id=case.case_id,
            passed=rejected_correctly,
            routing_correct=rejected_correctly,
            abstention_correct=None,
            citations_correct=None,
            scope_correct=None,
        )

    if case.expected_action == "reject":
        return AgentCaseResult(
            case_id=case.case_id,
            passed=False,
            routing_correct=False,
            abstention_correct=None,
            citations_correct=None,
            scope_correct=None,
        )

    routing_correct = _routing_is_correct(
        response=response,
        case=case,
    )

    abstention_correct = _abstention_is_correct(
        response=response,
        case=case,
    )

    citations_correct = _citations_are_correct(
        response=response,
        case=case,
    )

    scope_correct = _scope_is_correct(
        response=response,
        case=case,
    )

    checks = [
        routing_correct,
        *(
            [abstention_correct]
            if abstention_correct is not None
            else []
        ),
        *(
            [citations_correct]
            if citations_correct is not None
            else []
        ),
        *(
            [scope_correct]
            if scope_correct is not None
            else []
        ),
    ]

    return AgentCaseResult(
        case_id=case.case_id,
        passed=all(checks),
        routing_correct=routing_correct,
        abstention_correct=abstention_correct,
        citations_correct=citations_correct,
        scope_correct=scope_correct,
    )


def _routing_is_correct(
    response: AgentResponse,
    case: AgentEvaluationCase,
) -> bool:
    actual_versions = tuple(
        item.version
        for item in response.version_answers
    )

    action_correct = (
        response.action.value == case.expected_action
    )

    versions_correct = (
        actual_versions == case.expected_versions
    )

    if response.action == AgentAction.CLARIFY_VERSION:
        return (
            action_correct
            and versions_correct
            and bool(response.message)
        )

    return action_correct and versions_correct


def _abstention_is_correct(
    response: AgentResponse,
    case: AgentEvaluationCase,
) -> bool | None:
    if case.expected_answered is None:
        return None

    return all(
        item.response.answered
        is case.expected_answered
        for item in response.version_answers
    )


def _citations_are_correct(
    response: AgentResponse,
    case: AgentEvaluationCase,
) -> bool | None:
    if case.expected_answered is None:
        return None

    citations = [
        citation
        for item in response.version_answers
        for citation in item.response.citations
    ]

    if case.expect_citations:
        return bool(citations)

    return not citations


def _scope_is_correct(
    response: AgentResponse,
    case: AgentEvaluationCase,
) -> bool | None:
    if not case.expect_citations:
        return None

    return all(
        citation.product == case.product
        and citation.version == item.version
        for item in response.version_answers
        for citation in item.response.citations
    )


def _accuracy(values: list[bool]) -> float:
    if not values:
        return 1.0

    return sum(values) / len(values)