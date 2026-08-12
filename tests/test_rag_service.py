from app.generation import Evidence, GeneratedDraft
from app.models import DocumentChunk
from app.rag_service import ABSTENTION_MESSAGE, RAGService
from app.vector_store import RetrievalResult


AUTH_CHUNK = DocumentChunk(
    chunk_id="auth-v2",
    product="examplecloud",
    version="v2",
    source="examplecloud/v2/api-guide.md",
    title="ExampleCloud API Guide",
    section="Authentication",
    text=(
        "ExampleCloud API version 2 uses OAuth 2.0 bearer "
        "tokens."
    ),
)

EXPORT_CHUNK = DocumentChunk(
    chunk_id="export-v2",
    product="examplecloud",
    version="v2",
    source="examplecloud/v2/api-guide.md",
    title="ExampleCloud API Guide",
    section="Data export",
    text="Version 2 supports both CSV and JSON exports.",
)


class FakeVectorStore:
    """Return predetermined results without running embeddings."""

    def __init__(
        self,
        results: list[RetrievalResult],
    ) -> None:
        self.results = results
        self.received_search: dict | None = None

    def search(
        self,
        query: str,
        product: str,
        version: str,
        limit: int,
    ) -> list[RetrievalResult]:
        self.received_search = {
            "query": query,
            "product": product,
            "version": version,
            "limit": limit,
        }

        return self.results[:limit]


class FakeAnswerGenerator:
    """Return a predetermined structured LLM response."""

    def __init__(
        self,
        draft: GeneratedDraft,
    ) -> None:
        self.draft = draft
        self.received_question: str | None = None
        self.received_evidence: list[Evidence] | None = None

    def generate(
        self,
        question: str,
        evidence: list[Evidence],
    ) -> GeneratedDraft:
        self.received_question = question
        self.received_evidence = evidence

        return self.draft


def test_returns_grounded_answer_with_trusted_citation() -> None:
    vector_store = FakeVectorStore(
        results=[
            RetrievalResult(
                chunk=AUTH_CHUNK,
                score=0.82,
            )
        ]
    )

    generator = FakeAnswerGenerator(
        draft=GeneratedDraft(
            answer=(
                "ExampleCloud v2 uses OAuth 2.0 bearer tokens."
            ),
            cited_evidence_ids=("E1",),
        )
    )

    service = RAGService(
        vector_store=vector_store,
        answer_generator=generator,
    )

    response = service.answer(
        question="How do I authenticate?",
        product="examplecloud",
        version="v2",
    )

    assert response.answered is True
    assert "OAuth 2.0" in response.answer
    assert len(response.citations) == 1

    citation = response.citations[0]

    assert citation.evidence_id == "E1"
    assert citation.version == "v2"
    assert citation.section == "Authentication"
    assert (
        citation.source
        == "examplecloud/v2/api-guide.md"
    )


def test_passes_product_and_version_to_retrieval() -> None:
    vector_store = FakeVectorStore(
        results=[
            RetrievalResult(
                chunk=AUTH_CHUNK,
                score=0.82,
            )
        ]
    )

    generator = FakeAnswerGenerator(
        draft=GeneratedDraft(
            answer="Use OAuth 2.0 bearer tokens.",
            cited_evidence_ids=("E1",),
        )
    )

    service = RAGService(
        vector_store=vector_store,
        answer_generator=generator,
        retrieval_limit=3,
    )

    service.answer(
        question="Which credentials should I send?",
        product="examplecloud",
        version="v2",
    )

    assert vector_store.received_search == {
        "query": "Which credentials should I send?",
        "product": "examplecloud",
        "version": "v2",
        "limit": 3,
    }


def test_numbers_selected_evidence_in_ranked_order() -> None:
    vector_store = FakeVectorStore(
        results=[
            RetrievalResult(
                chunk=AUTH_CHUNK,
                score=0.82,
            ),
            RetrievalResult(
                chunk=EXPORT_CHUNK,
                score=0.51,
            ),
        ]
    )

    generator = FakeAnswerGenerator(
        draft=GeneratedDraft(
            answer="Use OAuth 2.0 bearer tokens.",
            cited_evidence_ids=("E1",),
        )
    )

    service = RAGService(
        vector_store=vector_store,
        answer_generator=generator,
        minimum_score=0.35,
    )

    service.answer(
        question="How do I authenticate?",
        product="examplecloud",
        version="v2",
    )

    assert generator.received_evidence is not None

    assert [
        item.evidence_id
        for item in generator.received_evidence
    ] == ["E1", "E2"]

    assert (
        generator.received_evidence[0].section
        == "Authentication"
    )


def test_excludes_results_below_threshold() -> None:
    vector_store = FakeVectorStore(
        results=[
            RetrievalResult(
                chunk=AUTH_CHUNK,
                score=0.82,
            ),
            RetrievalResult(
                chunk=EXPORT_CHUNK,
                score=0.12,
            ),
        ]
    )

    generator = FakeAnswerGenerator(
        draft=GeneratedDraft(
            answer="Use OAuth 2.0 bearer tokens.",
            cited_evidence_ids=("E1",),
        )
    )

    service = RAGService(
        vector_store=vector_store,
        answer_generator=generator,
        minimum_score=0.35,
    )

    service.answer(
        question="How do I authenticate?",
        product="examplecloud",
        version="v2",
    )

    assert generator.received_evidence is not None
    assert len(generator.received_evidence) == 1
    assert (
        generator.received_evidence[0].section
        == "Authentication"
    )


def test_abstains_when_no_result_meets_threshold() -> None:
    vector_store = FakeVectorStore(
        results=[
            RetrievalResult(
                chunk=EXPORT_CHUNK,
                score=0.12,
            )
        ]
    )

    generator = FakeAnswerGenerator(
        draft=GeneratedDraft(
            answer="This should never be used.",
            cited_evidence_ids=("E1",),
        )
    )

    service = RAGService(
        vector_store=vector_store,
        answer_generator=generator,
        minimum_score=0.35,
    )

    response = service.answer(
        question="What is the stock price?",
        product="examplecloud",
        version="v2",
    )

    assert response.answered is False
    assert response.answer == ABSTENTION_MESSAGE
    assert response.citations == ()
    assert generator.received_question is None


def test_abstains_when_generator_returns_no_citation() -> None:
    vector_store = FakeVectorStore(
        results=[
            RetrievalResult(
                chunk=AUTH_CHUNK,
                score=0.82,
            )
        ]
    )

    generator = FakeAnswerGenerator(
        draft=GeneratedDraft(
            answer="Use OAuth 2.0 bearer tokens.",
            cited_evidence_ids=(),
        )
    )

    service = RAGService(
        vector_store=vector_store,
        answer_generator=generator,
    )

    response = service.answer(
        question="How do I authenticate?",
        product="examplecloud",
        version="v2",
    )

    assert response.answered is False
    assert response.citations == ()


def test_rejects_hallucinated_evidence_id() -> None:
    vector_store = FakeVectorStore(
        results=[
            RetrievalResult(
                chunk=AUTH_CHUNK,
                score=0.82,
            )
        ]
    )

    generator = FakeAnswerGenerator(
        draft=GeneratedDraft(
            answer="Use OAuth 2.0 bearer tokens.",
            cited_evidence_ids=("E99",),
        )
    )

    service = RAGService(
        vector_store=vector_store,
        answer_generator=generator,
    )

    response = service.answer(
        question="How do I authenticate?",
        product="examplecloud",
        version="v2",
    )

    assert response.answered is False
    assert response.citations == ()


def test_abstains_when_generated_answer_is_empty() -> None:
    vector_store = FakeVectorStore(
        results=[
            RetrievalResult(
                chunk=AUTH_CHUNK,
                score=0.82,
            )
        ]
    )

    generator = FakeAnswerGenerator(
        draft=GeneratedDraft(
            answer="   ",
            cited_evidence_ids=("E1",),
        )
    )

    service = RAGService(
        vector_store=vector_store,
        answer_generator=generator,
    )

    response = service.answer(
        question="How do I authenticate?",
        product="examplecloud",
        version="v2",
    )

    assert response.answered is False


def test_removes_duplicate_citation_ids() -> None:
    vector_store = FakeVectorStore(
        results=[
            RetrievalResult(
                chunk=AUTH_CHUNK,
                score=0.82,
            )
        ]
    )

    generator = FakeAnswerGenerator(
        draft=GeneratedDraft(
            answer="Use OAuth 2.0 bearer tokens.",
            cited_evidence_ids=("E1", "E1"),
        )
    )

    service = RAGService(
        vector_store=vector_store,
        answer_generator=generator,
    )

    response = service.answer(
        question="How do I authenticate?",
        product="examplecloud",
        version="v2",
    )

    assert response.answered is True
    assert len(response.citations) == 1