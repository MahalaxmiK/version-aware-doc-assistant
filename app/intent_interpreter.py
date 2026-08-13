import os
from dataclasses import dataclass
from typing import Protocol

from openai import OpenAI
from pydantic import BaseModel, Field


DEFAULT_INTENT_MODEL = "gpt-5.6-luna"


@dataclass(frozen=True)
class InterpretedIntent:
    """Structured intent extracted from a user question."""

    requested_versions: tuple[str, ...]
    comparison_requested: bool


class IntentInterpreter(Protocol):
    """Interface for natural-language intent interpretation."""

    def interpret(
        self,
        question: str,
        product: str,
        available_versions: tuple[str, ...],
    ) -> InterpretedIntent:
        ...


class StructuredIntent(BaseModel):
    """Schema enforced on model-generated routing intent."""

    requested_versions: list[str] = Field(
        description=(
            "Documentation versions explicitly mentioned by "
            "the user. Use only available versions."
        )
    )

    comparison_requested: bool = Field(
        description=(
            "True only when the user explicitly asks to compare "
            "two or more documentation versions."
        )
    )


SYSTEM_INSTRUCTIONS = """
You interpret routing intent for a documentation assistant.

Rules:
1. Extract only documentation versions explicitly mentioned by the user.
2. Use only versions listed as available.
3. Do not guess or select a default version.
4. Set comparison_requested to true only when the user explicitly asks
   to compare, contrast, or identify differences between versions.
5. Do not answer the user's technical question.
6. Do not retrieve documents or generate citations.
""".strip()


class OpenAIIntentInterpreter:
    """Extract bounded routing intent with structured output."""

    def __init__(
        self,
        client: OpenAI | None = None,
        model: str | None = None,
    ) -> None:
        self.client = client or OpenAI()

        self.model = (
            model
            or os.getenv(
                "OPENAI_MODEL",
                DEFAULT_INTENT_MODEL,
            )
        )

    def interpret(
        self,
        question: str,
        product: str,
        available_versions: tuple[str, ...],
    ) -> InterpretedIntent:
        """Interpret a question without executing any workflow."""

        response = self.client.responses.parse(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": SYSTEM_INSTRUCTIONS,
                },
                {
                    "role": "user",
                    "content": self._build_user_message(
                        question=question,
                        product=product,
                        available_versions=available_versions,
                    ),
                },
            ],
            text_format=StructuredIntent,
        )

        parsed = response.output_parsed

        if parsed is None:
            return InterpretedIntent(
                requested_versions=(),
                comparison_requested=False,
            )

        return InterpretedIntent(
            requested_versions=tuple(
                parsed.requested_versions
            ),
            comparison_requested=(
                parsed.comparison_requested
            ),
        )

    @staticmethod
    def _build_user_message(
        question: str,
        product: str,
        available_versions: tuple[str, ...],
    ) -> str:
        """Create a delimited routing request."""

        versions = ", ".join(available_versions)

        return "\n".join(
            [
                f"Product: {product}",
                f"Available versions: {versions}",
                "",
                "<question>",
                question.strip(),
                "</question>",
            ]
        )