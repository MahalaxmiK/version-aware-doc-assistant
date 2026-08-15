from pathlib import Path

from app.agent_evaluation import (
    evaluate_agent_cases,
    load_agent_cases,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = (
    PROJECT_ROOT / "evaluation" / "agent_cases.json"
)


def main() -> None:
    cases = load_agent_cases(CASES_PATH)
    report = evaluate_agent_cases(cases)

    print("Agent workflow evaluation")
    print("-------------------------")
    print(f"Cases: {report.case_count}")
    print(
        f"Passed: "
        f"{report.passed_count}/{report.case_count}"
    )
    print(
        f"Workflow accuracy: "
        f"{report.workflow_accuracy:.1%}"
    )
    print(
        f"Routing accuracy: "
        f"{report.routing_accuracy:.1%}"
    )
    print(
        f"Abstention accuracy: "
        f"{report.abstention_accuracy:.1%}"
    )
    print(
        f"Citation presence accuracy: "
        f"{report.citation_accuracy:.1%}"
    )
    print(
        f"Citation scope accuracy: "
        f"{report.scope_accuracy:.1%}"
    )

    if report.failed_case_ids:
        print(
            "Failed cases: "
            + ", ".join(report.failed_case_ids)
        )
    else:
        print("Failed cases: none")


if __name__ == "__main__":
    main()