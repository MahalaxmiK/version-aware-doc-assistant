from app.agent_models import AgentAction
from app.agent_router import AgentRouter
from app.agent_service import AgentService
from app.intent_interpreter import InterpretedIntent
from app.rag_service import RAGResponse


class FakeIntentInterpreter:
    """Return predetermined intent without calling OpenAI."""

    def __init__(
        self,
        intent: InterpretedIntent,
    ) -> None:
        self.intent = intent
        self.calls: list[
            tuple[str, str, tuple[str, ...]]
        ] = []

    def interpret(
        self,
        question: str,
        product: str,
        available_versions: tuple[str, ...],
    ) -> InterpretedIntent:
        self.calls.append(
            (
                question,
                product,
                available_versions,
            )
        )

        return self.intent


class FakeRAGService:
    """Record independently scoped RAG calls."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def answer(
        self,
        question: str,
        product: str,
        version: str,
    ) -> RAGResponse:
        self.calls.append(
            (
                question,
                product,
                version,
            )
        )

        return RAGResponse(
            answered=True,
            answer=f"Answer for {version}.",
            citations=(),
            evidence=(),
        )


def make_service(
    intent: InterpretedIntent,
) -> tuple[
    AgentService,
    FakeIntentInterpreter,
    FakeRAGService,
]:
    router = AgentRouter(
        available_versions={
            "examplecloud": ("v1", "v2"),
        }
    )

    interpreter = FakeIntentInterpreter(intent)
    rag_service = FakeRAGService()

    service = AgentService(
        router=router,
        rag_service=rag_service,
        intent_interpreter=interpreter,
    )

    return service, interpreter, rag_service


def test_interpreted_single_version_executes_answer() -> None:
    service, interpreter, rag_service = make_service(
        InterpretedIntent(
            requested_versions=("v2",),
            comparison_requested=False,
        )
    )

    response = service.run_natural_language(
        question="How do I authenticate in v2?",
        product="examplecloud",
    )

    assert response.action == AgentAction.ANSWER

    assert interpreter.calls == [
        (
            "How do I authenticate in v2?",
            "examplecloud",
            ("v1", "v2"),
        )
    ]

    assert rag_service.calls == [
        (
            "How do I authenticate in v2?",
            "examplecloud",
            "v2",
        )
    ]


def test_missing_version_returns_clarification() -> None:
    service, _, rag_service = make_service(
        InterpretedIntent(
            requested_versions=(),
            comparison_requested=False,
        )
    )

    response = service.run_natural_language(
        question="How do I authenticate?",
        product="examplecloud",
    )

    assert (
        response.action
        == AgentAction.CLARIFY_VERSION
    )
    assert response.message is not None
    assert rag_service.calls == []


def test_interpreted_comparison_runs_isolated_searches() -> None:
    service, _, rag_service = make_service(
        InterpretedIntent(
            requested_versions=("v1", "v2"),
            comparison_requested=True,
        )
    )

    response = service.run_natural_language(
        question="Compare authentication in v1 and v2.",
        product="examplecloud",
    )

    assert (
        response.action
        == AgentAction.COMPARE_VERSIONS
    )

    assert rag_service.calls == [
        (
            "Compare authentication in v1 and v2.",
            "examplecloud",
            "v1",
        ),
        (
            "Compare authentication in v1 and v2.",
            "examplecloud",
            "v2",
        ),
    ]


def test_router_rejects_interpreter_invented_version() -> None:
    service, _, rag_service = make_service(
        InterpretedIntent(
            requested_versions=("v99",),
            comparison_requested=False,
        )
    )

    try:
        service.run_natural_language(
            question="Explain authentication in v99.",
            product="examplecloud",
        )
    except ValueError as error:
        assert "Unknown version" in str(error)
    else:
        raise AssertionError(
            "Expected invented version to be rejected"
        )

    assert rag_service.calls == []


def test_comparison_with_one_version_clarifies() -> None:
    service, _, rag_service = make_service(
        InterpretedIntent(
            requested_versions=("v2",),
            comparison_requested=True,
        )
    )

    response = service.run_natural_language(
        question="Compare authentication in v2.",
        product="examplecloud",
    )

    assert (
        response.action
        == AgentAction.CLARIFY_VERSION
    )
    assert rag_service.calls == []


def test_rejects_unknown_product_before_interpretation() -> None:
    service, interpreter, rag_service = make_service(
        InterpretedIntent(
            requested_versions=("v1",),
            comparison_requested=False,
        )
    )

    try:
        service.run_natural_language(
            question="How do I authenticate?",
            product="unknowncloud",
        )
    except ValueError as error:
        assert "Unknown product" in str(error)
    else:
        raise AssertionError(
            "Expected unknown product to be rejected"
        )

    assert interpreter.calls == []
    assert rag_service.calls == []


def test_requires_configured_interpreter() -> None:
    service = AgentService(
        router=AgentRouter(
            available_versions={
                "examplecloud": ("v1", "v2"),
            }
        ),
        rag_service=FakeRAGService(),
    )

    try:
        service.run_natural_language(
            question="How do I authenticate in v2?",
            product="examplecloud",
        )
    except RuntimeError as error:
        assert "not configured" in str(error)
    else:
        raise AssertionError(
            "Expected missing interpreter to be rejected"
        )