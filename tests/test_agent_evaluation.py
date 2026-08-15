from pathlib import Path

import pytest

from app.agent_evaluation import (
    evaluate_agent_cases,
    load_agent_cases,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = (
    PROJECT_ROOT / "evaluation" / "agent_cases.json"
)


def test_loads_agent_evaluation_cases() -> None:
    cases = load_agent_cases(CASES_PATH)

    assert len(cases) == 12

    expected_actions = {
        case.expected_action for case in cases
    }

    assert expected_actions == {
        "answer",
        "clarify_version",
        "compare_versions",
        "reject",
    }


def test_agent_workflow_evaluation_meets_baseline() -> None:
    cases = load_agent_cases(CASES_PATH)
    report = evaluate_agent_cases(cases)

    assert report.case_count == 12
    assert report.passed_count == 12
    assert report.workflow_accuracy == 1.0
    assert report.routing_accuracy == 1.0
    assert report.abstention_accuracy == 1.0
    assert report.citation_accuracy == 1.0
    assert report.scope_accuracy == 1.0
    assert report.failed_case_ids == []


def test_rejects_empty_agent_evaluation() -> None:
    with pytest.raises(
        ValueError,
        match="At least one agent evaluation case is required",
    ):
        evaluate_agent_cases([])