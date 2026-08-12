from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Evidence:
    """A numbered evidence passage supplied to the generator."""

    evidence_id: str
    chunk_id: str
    product: str
    version: str
    source: str
    title: str
    section: str
    text: str
    score: float


@dataclass(frozen=True)
class GeneratedDraft:
    """Structured draft returned by an answer generator."""

    answer: str
    cited_evidence_ids: tuple[str, ...]


class AnswerGenerator(Protocol):
    """Interface implemented by any supported LLM provider."""

    def generate(
        self,
        question: str,
        evidence: list[Evidence],
    ) -> GeneratedDraft:
        """Generate an answer using only the supplied evidence."""
        ...