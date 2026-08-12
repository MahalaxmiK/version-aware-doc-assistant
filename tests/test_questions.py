from fastapi.testclient import TestClient

from app.dependencies import get_rag_service
from app.main import app
from app.rag_service import Citation, RAGResponse


class StubRAGService:
    """Predictable RAG service used by endpoint tests."""

    def __init__(self) -> None:
        self.received_question: str | None = None
        self.received_product: str | None = None
        self.received_version: str | None = None

    def answer(
        self,
        question: str,
        product: str,
        version: str,
    ) -> RAGResponse:
        self.received_question = question
        self.received_product = product
        self.received_version = version

        return RAGResponse(
            answered=True,
            answer=(
                "Version 2 uses OAuth 2.0 bearer tokens."
            ),
            citations=(
                Citation(
                    evidence_id="E1",
                    product="examplecloud",
                    version="v2",
                    source="examplecloud/v2/api-guide.md",
                    title="ExampleCloud API Guide",
                    section="Authentication",
                ),
            ),
            evidence=(),
        )


client = TestClient(app)


def test_questions_endpoint_returns_grounded_response() -> None:
    stub_service = StubRAGService()

    app.dependency_overrides[get_rag_service] = (
        lambda: stub_service
    )

    try:
        response = client.post(
            "/questions",
            json={
                "question": "How do I authenticate?",
                "product": "examplecloud",
                "version": "v2",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

    assert response.json() == {
        "answered": True,
        "answer": (
            "Version 2 uses OAuth 2.0 bearer tokens."
        ),
        "citations": [
            {
                "evidence_id": "E1",
                "product": "examplecloud",
                "version": "v2",
                "source": "examplecloud/v2/api-guide.md",
                "title": "ExampleCloud API Guide",
                "section": "Authentication",
            }
        ],
    }


def test_questions_endpoint_passes_scope_to_service() -> None:
    stub_service = StubRAGService()

    app.dependency_overrides[get_rag_service] = (
        lambda: stub_service
    )

    try:
        response = client.post(
            "/questions",
            json={
                "question": "  How do I authenticate?  ",
                "product": "  examplecloud  ",
                "version": "  v2  ",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert (
        stub_service.received_question
        == "How do I authenticate?"
    )
    assert stub_service.received_product == "examplecloud"
    assert stub_service.received_version == "v2"


def test_questions_endpoint_rejects_blank_question() -> None:
    response = client.post(
        "/questions",
        json={
            "question": "   ",
            "product": "examplecloud",
            "version": "v2",
        },
    )

    assert response.status_code == 422


def test_questions_endpoint_requires_version() -> None:
    response = client.post(
        "/questions",
        json={
            "question": "How do I authenticate?",
            "product": "examplecloud",
        },
    )

    assert response.status_code == 422