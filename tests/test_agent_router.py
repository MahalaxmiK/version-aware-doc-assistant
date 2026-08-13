import pytest

from app.agent_models import AgentAction
from app.agent_router import AgentRouter


@pytest.fixture
def router() -> AgentRouter:
    return AgentRouter(
        available_versions={
            "examplecloud": ("v1", "v2"),
        }
    )


def test_routes_one_version_to_answer(
    router: AgentRouter,
) -> None:
    decision = router.route(
        product="examplecloud",
        requested_versions=("v2",),
    )

    assert decision.action == AgentAction.ANSWER
    assert decision.versions == ("v2",)


def test_missing_version_requests_clarification(
    router: AgentRouter,
) -> None:
    decision = router.route(
        product="examplecloud",
        requested_versions=(),
    )

    assert decision.action == AgentAction.CLARIFY_VERSION
    assert decision.versions == ()
    assert decision.message is not None
    assert "v1, v2" in decision.message


def test_explicit_comparison_routes_to_comparison(
    router: AgentRouter,
) -> None:
    decision = router.route(
        product="examplecloud",
        requested_versions=("v1", "v2"),
        comparison_requested=True,
    )

    assert decision.action == AgentAction.COMPARE_VERSIONS
    assert decision.versions == ("v1", "v2")


def test_comparison_with_one_version_requests_clarification(
    router: AgentRouter,
) -> None:
    decision = router.route(
        product="examplecloud",
        requested_versions=("v2",),
        comparison_requested=True,
    )

    assert decision.action == AgentAction.CLARIFY_VERSION
    assert "at least two" in (decision.message or "")


def test_multiple_versions_without_comparison_are_ambiguous(
    router: AgentRouter,
) -> None:
    decision = router.route(
        product="examplecloud",
        requested_versions=("v1", "v2"),
        comparison_requested=False,
    )

    assert decision.action == AgentAction.CLARIFY_VERSION
    assert "explicitly request" in (decision.message or "")


def test_rejects_unknown_product(
    router: AgentRouter,
) -> None:
    with pytest.raises(
        ValueError,
        match="Unknown product",
    ):
        router.route(
            product="unknowncloud",
            requested_versions=("v1",),
        )


def test_rejects_unknown_version(
    router: AgentRouter,
) -> None:
    with pytest.raises(
        ValueError,
        match="Unknown version",
    ):
        router.route(
            product="examplecloud",
            requested_versions=("v99",),
        )


def test_normalizes_and_deduplicates_versions(
    router: AgentRouter,
) -> None:
    decision = router.route(
        product=" examplecloud ",
        requested_versions=(" v2 ", "v2"),
    )

    assert decision.action == AgentAction.ANSWER
    assert decision.product == "examplecloud"
    assert decision.versions == ("v2",)