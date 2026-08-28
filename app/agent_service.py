from dataclasses import dataclass
from typing import Protocol

from langsmith import traceable

from app.agent_models import AgentAction
from app.agent_router import AgentRouter
from app.intent_interpreter import IntentInterpreter
from app.observability import (
    summarize_agent_inputs,
    summarize_agent_output,
)
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
    """Interpret, route, and execute bounded workflows."""

    def __init__(
        self,
        router: AgentRouter,
        rag_service: RAGAnswerer,
        intent_interpreter: IntentInterpreter | None = None,
    ) -> None:
        self.router = router
        self.rag_service = rag_service
        self.intent_interpreter = intent_interpreter

    @traceable(
        name="agent.workflow",
        run_type="chain",
        process_inputs=summarize_agent_inputs,
        process_outputs=summarize_agent_output,
    )
    def run_natural_language(
        self,
        question: str,
        product: str,
    ) -> AgentResponse:
        """Interpret natural language, then execute a safe route."""

        normalized_question = question.strip()
        normalized_product = product.strip()

        if not normalized_question:
            raise ValueError("Question cannot be empty")

        if not normalized_product:
            raise ValueError("Product cannot be empty")

        if self.intent_interpreter is None:
            raise RuntimeError(
                "Natural-language intent interpreter is not configured"
            )

        available_versions = self._available_versions(
            normalized_product
        )

        intent = self.intent_interpreter.interpret(
            question=normalized_question,
            product=normalized_product,
            available_versions=available_versions,
        )

        focused_question = intent.focused_question.strip()

        if not focused_question:
            raise ValueError(
                "Interpreted focused question cannot be empty"
            )

        return self.run(
            question=focused_question,
            product=normalized_product,
            requested_versions=intent.requested_versions,
            comparison_requested=(
                intent.comparison_requested
            ),
        )

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

    def _available_versions(
        self,
        product: str,
    ) -> tuple[str, ...]:
        """Return configured versions for intent interpretation."""

        if product not in self.router.available_versions:
            raise ValueError(f"Unknown product: {product}")

        return self.router.available_versions[product]
