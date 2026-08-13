from dataclasses import dataclass
from enum import Enum


class AgentAction(str, Enum):
    """Actions the bounded documentation agent may choose."""

    ANSWER = "answer"
    CLARIFY_VERSION = "clarify_version"
    COMPARE_VERSIONS = "compare_versions"


@dataclass(frozen=True)
class AgentDecision:
    """A validated routing decision made before retrieval."""

    action: AgentAction
    product: str
    versions: tuple[str, ...]
    message: str | None = None

    def __post_init__(self) -> None:
        if not self.product.strip():
            raise ValueError("Product cannot be empty")

        if self.action == AgentAction.ANSWER:
            if len(self.versions) != 1:
                raise ValueError(
                    "Answer action requires exactly one version"
                )

        if self.action == AgentAction.CLARIFY_VERSION:
            if self.versions:
                raise ValueError(
                    "Clarification cannot select a version"
                )

            if not self.message:
                raise ValueError(
                    "Clarification requires a message"
                )

        if self.action == AgentAction.COMPARE_VERSIONS:
            if len(self.versions) < 2:
                raise ValueError(
                    "Comparison requires at least two versions"
                )