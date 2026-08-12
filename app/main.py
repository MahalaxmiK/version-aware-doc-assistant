from typing import Annotated

from fastapi import Depends, FastAPI

from app.api_models import (
    CitationResponse,
    QuestionRequest,
    QuestionResponse,
)
from app.dependencies import get_rag_service
from app.rag_service import RAGService


app = FastAPI(
    title="Version-Aware Documentation Assistant",
    description=(
        "A controlled RAG service that answers technical questions "
        "using documentation from a selected product version."
    ),
    version="0.2.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Confirm that the API process is running."""

    return {
        "status": "healthy",
        "service": "version-aware-doc-assistant",
    }


@app.post(
    "/questions",
    response_model=QuestionResponse,
)
def answer_question(
    request: QuestionRequest,
    rag_service: Annotated[
        RAGService,
        Depends(get_rag_service),
    ],
) -> QuestionResponse:
    """Answer a question using version-filtered documentation."""

    result = rag_service.answer(
        question=request.question,
        product=request.product,
        version=request.version,
    )

    citations = [
        CitationResponse(
            evidence_id=citation.evidence_id,
            product=citation.product,
            version=citation.version,
            source=citation.source,
            title=citation.title,
            section=citation.section,
        )
        for citation in result.citations
    ]

    return QuestionResponse(
        answered=result.answered,
        answer=result.answer,
        citations=citations,
    )