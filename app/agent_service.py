from dataclasses import dataclass
from typing import Protocol

from app.agent_models import AgentAction
from app.agent_router import AgentRouter
from app.rag_service import RAGResponse


class RAGAnswerer(Protocol):
    """Interface required from a version-scoped RAG service."""

    def answer(
        self,
        question: str,
        product: str,
        version: str,
    ) -> RAGResponse:
        ...


@dataclass(frozen=True)
class VersionAnswer:
    """A grounded RAG response for one documentation version."""

    version: str
    response: RAGResponse


@dataclass(frozen=True)
class AgentResponse:
    """Result of executing one bounded agent workflow."""

    action: AgentAction
    message: str | None
    version_answers: tuple[VersionAnswer, ...]


class AgentService:
    """Route and execute bounded documentation workflows."""

    def __init__(
        self,
        router: AgentRouter,
        rag_service: RAGAnswerer,
    ) -> None:
        self.router = router
        self.rag_service = rag_service

    def run(
        self,
        question: str,
        product: str,
        requested_versions: tuple[str, ...],
        comparison_requested: bool = False,
    ) -> AgentResponse:
        """Execute only the workflow permitted by the router."""

        normalized_question = question.strip()

        if not normalized_question:
            raise ValueError("Question cannot be empty")

        decision = self.router.route(
            product=product,
            requested_versions=requested_versions,
            comparison_requested=comparison_requested,
        )

        if decision.action == AgentAction.CLARIFY_VERSION:
            return AgentResponse(
                action=decision.action,
                message=decision.message,
                version_answers=(),
            )

        version_answers = tuple(
            VersionAnswer(
                version=version,
                response=self.rag_service.answer(
                    question=normalized_question,
                    product=decision.product,
                    version=version,
                ),
            )
            for version in decision.versions
        )

        return AgentResponse(
            action=decision.action,
            message=None,
            version_answers=version_answers,
        )