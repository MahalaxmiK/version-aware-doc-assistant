import pytest

from app.agent_models import AgentAction, AgentDecision


def test_answer_decision_requires_one_version() -> None:
    decision = AgentDecision(
        action=AgentAction.ANSWER,
        product="examplecloud",
        versions=("v2",),
    )

    assert decision.versions == ("v2",)


def test_answer_rejects_multiple_versions() -> None:
    with pytest.raises(
        ValueError,
        match="exactly one version",
    ):
        AgentDecision(
            action=AgentAction.ANSWER,
            product="examplecloud",
            versions=("v1", "v2"),
        )


def test_clarification_requires_no_selected_version() -> None:
    decision = AgentDecision(
        action=AgentAction.CLARIFY_VERSION,
        product="examplecloud",
        versions=(),
        message="Which version should I use?",
    )

    assert decision.action == AgentAction.CLARIFY_VERSION


def test_clarification_requires_message() -> None:
    with pytest.raises(
        ValueError,
        match="requires a message",
    ):
        AgentDecision(
            action=AgentAction.CLARIFY_VERSION,
            product="examplecloud",
            versions=(),
        )


def test_comparison_requires_multiple_versions() -> None:
    decision = AgentDecision(
        action=AgentAction.COMPARE_VERSIONS,
        product="examplecloud",
        versions=("v1", "v2"),
    )

    assert decision.versions == ("v1", "v2")


def test_comparison_rejects_one_version() -> None:
    with pytest.raises(
        ValueError,
        match="at least two versions",
    ):
        AgentDecision(
            action=AgentAction.COMPARE_VERSIONS,
            product="examplecloud",
            versions=("v2",),
        )


def test_rejects_empty_product() -> None:
    with pytest.raises(
        ValueError,
        match="Product cannot be empty",
    ):
        AgentDecision(
            action=AgentAction.ANSWER,
            product="   ",
            versions=("v2",),
        )