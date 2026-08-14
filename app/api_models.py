from pydantic import BaseModel, Field, field_validator
from app.agent_models import AgentAction


class QuestionRequest(BaseModel):
    """Input accepted by the documentation question endpoint."""

    question: str = Field(
        min_length=1,
        max_length=500,
        examples=["How do I authenticate?"],
    )
    product: str = Field(
        min_length=1,
        max_length=100,
        examples=["examplecloud"],
    )
    version: str = Field(
        min_length=1,
        max_length=50,
        examples=["v2"],
    )

    @field_validator(
        "question",
        "product",
        "version",
        mode="before",
    )
    @classmethod
    def reject_blank_values(cls, value: object) -> object:
        """Reject strings containing only whitespace."""

        if isinstance(value, str) and not value.strip():
            raise ValueError("Value cannot be blank")

        return value

    @field_validator(
        "question",
        "product",
        "version",
    )
    @classmethod
    def normalize_text(cls, value: str) -> str:
        """Remove unnecessary surrounding whitespace."""

        return value.strip()


class CitationResponse(BaseModel):
    """A trusted citation returned with an answer."""

    evidence_id: str
    product: str
    version: str
    source: str
    title: str
    section: str


class QuestionResponse(BaseModel):
    """Public API response produced by the RAG pipeline."""

    answered: bool
    answer: str
    citations: list[CitationResponse]

class AgentQuestionRequest(BaseModel):
    """Natural-language request handled by the bounded agent."""

    question: str = Field(
        min_length=1,
        max_length=500,
        examples=[
            "Compare authentication between v1 and v2."
        ],
    )
    product: str = Field(
        min_length=1,
        max_length=100,
        examples=["examplecloud"],
    )

    @field_validator(
        "question",
        "product",
        mode="before",
    )
    @classmethod
    def reject_blank_values(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise ValueError("Value cannot be blank")

        return value

    @field_validator("question", "product")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()


class VersionAnswerResponse(BaseModel):
    """One independently grounded answer for one version."""

    version: str
    answered: bool
    answer: str
    citations: list[CitationResponse]


class AgentQuestionResponse(BaseModel):
    """Public response from the bounded agent workflow."""

    action: AgentAction
    message: str | None
    version_answers: list[VersionAnswerResponse]