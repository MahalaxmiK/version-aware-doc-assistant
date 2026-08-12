from pydantic import BaseModel, Field, field_validator


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