from dataclasses import dataclass

from app.generation import (
    AnswerGenerator,
    Evidence,
    GeneratedDraft,
)
from app.vector_store import RetrievalResult, VectorStore


DEFAULT_RETRIEVAL_LIMIT = 3
DEFAULT_MINIMUM_SCORE = 0.25

ABSTENTION_MESSAGE = (
    "I could not find sufficient information in the selected "
    "documentation to answer that question."
)


@dataclass(frozen=True)
class Citation:
    """Trusted citation reconstructed from retrieved evidence."""

    evidence_id: str
    product: str
    version: str
    source: str
    title: str
    section: str


@dataclass(frozen=True)
class RAGResponse:
    """Final response returned by the controlled RAG pipeline."""

    answered: bool
    answer: str
    citations: tuple[Citation, ...]
    evidence: tuple[Evidence, ...]


class RAGService:
    """Coordinate retrieval, evidence selection, and generation."""

    def __init__(
        self,
        vector_store: VectorStore,
        answer_generator: AnswerGenerator,
        retrieval_limit: int = DEFAULT_RETRIEVAL_LIMIT,
        minimum_score: float = DEFAULT_MINIMUM_SCORE,
    ) -> None:
        if retrieval_limit < 1:
            raise ValueError("Retrieval limit must be at least 1")

        if not 0.0 <= minimum_score <= 1.0:
            raise ValueError(
                "Minimum score must be between 0.0 and 1.0"
            )

        self.vector_store = vector_store
        self.answer_generator = answer_generator
        self.retrieval_limit = retrieval_limit
        self.minimum_score = minimum_score

    def answer(
        self,
        question: str,
        product: str,
        version: str,
    ) -> RAGResponse:
        """Answer a question using only eligible retrieved evidence."""

        results = self.vector_store.search(
            query=question,
            product=product,
            version=version,
            limit=self.retrieval_limit,
        )

        selected_results = self._select_results(results)

        if not selected_results:
            return self._abstain()

        evidence = self._build_evidence(selected_results)

        draft = self.answer_generator.generate(
            question=question,
            evidence=evidence,
        )

        return self._finalize_response(
            draft=draft,
            evidence=evidence,
        )

    def _select_results(
        self,
        results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        """Keep only results that meet the evidence threshold."""

        return [
            result
            for result in results
            if result.score >= self.minimum_score
        ]

    @staticmethod
    def _build_evidence(
        results: list[RetrievalResult],
    ) -> list[Evidence]:
        """Convert ranked retrieval results into numbered evidence."""

        return [
            Evidence(
                evidence_id=f"E{index}",
                chunk_id=result.chunk.chunk_id,
                product=result.chunk.product,
                version=result.chunk.version,
                source=result.chunk.source,
                title=result.chunk.title,
                section=result.chunk.section,
                text=result.chunk.text,
                score=result.score,
            )
            for index, result in enumerate(results, start=1)
        ]

    def _finalize_response(
        self,
        draft: GeneratedDraft,
        evidence: list[Evidence],
    ) -> RAGResponse:
        """Validate model citations and construct the final response."""

        answer = draft.answer.strip()

        if not answer:
            return self._abstain(evidence)

        evidence_by_id = {
            item.evidence_id: item
            for item in evidence
        }

        cited_ids = tuple(
            dict.fromkeys(draft.cited_evidence_ids)
        )

        if not cited_ids:
            return self._abstain(evidence)

        invalid_ids = [
            evidence_id
            for evidence_id in cited_ids
            if evidence_id not in evidence_by_id
        ]

        if invalid_ids:
            return self._abstain(evidence)

        citations = tuple(
            self._to_citation(evidence_by_id[evidence_id])
            for evidence_id in cited_ids
        )

        return RAGResponse(
            answered=True,
            answer=answer,
            citations=citations,
            evidence=tuple(evidence),
        )

    @staticmethod
    def _to_citation(evidence: Evidence) -> Citation:
        """Build a citation from trusted evidence metadata."""

        return Citation(
            evidence_id=evidence.evidence_id,
            product=evidence.product,
            version=evidence.version,
            source=evidence.source,
            title=evidence.title,
            section=evidence.section,
        )

    @staticmethod
    def _abstain(
        evidence: list[Evidence] | None = None,
    ) -> RAGResponse:
        """Return a safe response when grounded answering is impossible."""

        return RAGResponse(
            answered=False,
            answer=ABSTENTION_MESSAGE,
            citations=(),
            evidence=tuple(evidence or []),
        )