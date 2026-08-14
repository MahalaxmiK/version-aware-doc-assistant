from app.agent_models import AgentAction
from app.agent_router import AgentRouter
from app.agent_service import AgentService
from app.rag_service import Citation, RAGResponse


class FakeRAGService:
    """Record version-scoped calls and return grounded fakes."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def answer(
        self,
        question: str,
        product: str,
        version: str,
    ) -> RAGResponse:
        self.calls.append(
            (question, product, version)
        )

        return RAGResponse(
            answered=True,
            answer=f"Grounded answer for {version}.",
            citations=(
                Citation(
                    evidence_id="E1",
                    product=product,
                    version=version,
                    source=(
                        f"{product}/{version}/api-guide.md"
                    ),
                    title="ExampleCloud API Guide",
                    section="Authentication",
                ),
            ),
            evidence=(),
        )


def make_service() -> tuple[AgentService, FakeRAGService]:
    router = AgentRouter(
        available_versions={
            "examplecloud": ("v1", "v2"),
        }
    )

    rag_service = FakeRAGService()

    return (
        AgentService(
            router=router,
            rag_service=rag_service,
        ),
        rag_service,
    )


def test_executes_single_version_answer() -> None:
    service, rag_service = make_service()

    response = service.run(
        question="How do I authenticate?",
        product="examplecloud",
        requested_versions=("v2",),
    )

    assert response.action == AgentAction.ANSWER
    assert response.message is None
    assert len(response.version_answers) == 1
    assert response.version_answers[0].version == "v2"

    assert rag_service.calls == [
        (
            "How do I authenticate?",
            "examplecloud",
            "v2",
        )
    ]


def test_clarification_does_not_call_rag() -> None:
    service, rag_service = make_service()

    response = service.run(
        question="How do I authenticate?",
        product="examplecloud",
        requested_versions=(),
    )

    assert (
        response.action
        == AgentAction.CLARIFY_VERSION
    )
    assert response.message is not None
    assert response.version_answers == ()
    assert rag_service.calls == []


def test_comparison_calls_each_version_separately() -> None:
    service, rag_service = make_service()

    response = service.run(
        question="Compare authentication.",
        product="examplecloud",
        requested_versions=("v1", "v2"),
        comparison_requested=True,
    )

    assert (
        response.action
        == AgentAction.COMPARE_VERSIONS
    )

    assert [
        item.version
        for item in response.version_answers
    ] == ["v1", "v2"]

    assert rag_service.calls == [
        (
            "Compare authentication.",
            "examplecloud",
            "v1",
        ),
        (
            "Compare authentication.",
            "examplecloud",
            "v2",
        ),
    ]


def test_comparison_preserves_version_specific_citations() -> None:
    service, _ = make_service()

    response = service.run(
        question="Compare authentication.",
        product="examplecloud",
        requested_versions=("v1", "v2"),
        comparison_requested=True,
    )

    first_citation = (
        response.version_answers[0]
        .response.citations[0]
    )

    second_citation = (
        response.version_answers[1]
        .response.citations[0]
    )

    assert first_citation.version == "v1"
    assert second_citation.version == "v2"

    assert "/v1/" in first_citation.source
    assert "/v2/" in second_citation.source


def test_ambiguous_versions_do_not_call_rag() -> None:
    service, rag_service = make_service()

    response = service.run(
        question="How do I authenticate?",
        product="examplecloud",
        requested_versions=("v1", "v2"),
        comparison_requested=False,
    )

    assert (
        response.action
        == AgentAction.CLARIFY_VERSION
    )
    assert response.version_answers == ()
    assert rag_service.calls == []


def test_rejects_blank_question_before_routing() -> None:
    service, rag_service = make_service()

    try:
        service.run(
            question="   ",
            product="examplecloud",
            requested_versions=("v2",),
        )
    except ValueError as error:
        assert str(error) == "Question cannot be empty"
    else:
        raise AssertionError(
            "Expected blank question to be rejected"
        )

    assert rag_service.calls == []


def test_normalizes_question_before_rag_call() -> None:
    service, rag_service = make_service()

    service.run(
        question="  How do I authenticate?  ",
        product="examplecloud",
        requested_versions=("v2",),
    )

    assert rag_service.calls[0][0] == (
        "How do I authenticate?"
    )