from fastapi.testclient import TestClient

from app.agent_models import AgentAction
from app.agent_service import AgentResponse, VersionAnswer
from app.dependencies import get_agent_service
from app.main import app
from app.rag_service import Citation, RAGResponse


class StubAgentService:
    def __init__(
        self,
        response: AgentResponse,
    ) -> None:
        self.response = response
        self.calls: list[tuple[str, str]] = []

    def run_natural_language(
        self,
        question: str,
        product: str,
    ) -> AgentResponse:
        self.calls.append((question, product))
        return self.response


client = TestClient(app)


def test_agent_endpoint_returns_single_version_answer() -> None:
    stub = StubAgentService(
        AgentResponse(
            action=AgentAction.ANSWER,
            message=None,
            version_answers=(
                VersionAnswer(
                    version="v2",
                    response=RAGResponse(
                        answered=True,
                        answer="Version 2 uses OAuth 2.0.",
                        citations=(
                            Citation(
                                evidence_id="E1",
                                product="examplecloud",
                                version="v2",
                                source=(
                                    "examplecloud/v2/"
                                    "api-guide.md"
                                ),
                                title="ExampleCloud API Guide",
                                section="Authentication",
                            ),
                        ),
                        evidence=(),
                    ),
                ),
            ),
        )
    )

    app.dependency_overrides[get_agent_service] = (
        lambda: stub
    )

    try:
        response = client.post(
            "/agent/questions",
            json={
                "question": "How do I authenticate in v2?",
                "product": "examplecloud",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()

    assert body["action"] == "answer"
    assert body["version_answers"][0]["version"] == "v2"
    assert (
        body["version_answers"][0]["citations"][0]["version"]
        == "v2"
    )


def test_agent_endpoint_returns_clarification() -> None:
    stub = StubAgentService(
        AgentResponse(
            action=AgentAction.CLARIFY_VERSION,
            message=(
                "Which documentation version should I use?"
            ),
            version_answers=(),
        )
    )

    app.dependency_overrides[get_agent_service] = (
        lambda: stub
    )

    try:
        response = client.post(
            "/agent/questions",
            json={
                "question": "How do I authenticate?",
                "product": "examplecloud",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()

    assert body["action"] == "clarify_version"
    assert body["message"] is not None
    assert body["version_answers"] == []


def test_agent_endpoint_normalizes_input() -> None:
    stub = StubAgentService(
        AgentResponse(
            action=AgentAction.CLARIFY_VERSION,
            message="Select a version.",
            version_answers=(),
        )
    )

    app.dependency_overrides[get_agent_service] = (
        lambda: stub
    )

    try:
        response = client.post(
            "/agent/questions",
            json={
                "question": "  How do I authenticate?  ",
                "product": "  examplecloud  ",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert stub.calls == [
        (
            "How do I authenticate?",
            "examplecloud",
        )
    ]


def test_agent_endpoint_rejects_blank_question() -> None:
    stub = StubAgentService(
        AgentResponse(
            action=AgentAction.CLARIFY_VERSION,
            message="Unused.",
            version_answers=(),
        )
    )

    app.dependency_overrides[get_agent_service] = (
        lambda: stub
    )

    try:
        response = client.post(
            "/agent/questions",
            json={
                "question": "   ",
                "product": "examplecloud",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert stub.calls == []