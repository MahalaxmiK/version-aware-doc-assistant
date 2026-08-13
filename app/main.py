from typing import Annotated

from fastapi import Depends, FastAPI

from app.agent_service import AgentService

from app.api_models import (
    CitationResponse,
    QuestionRequest,
    QuestionResponse,
    AgentQuestionRequest,
    AgentQuestionResponse,
    VersionAnswerResponse,
)
from app.dependencies import (
    get_agent_service,
    get_rag_service,
)
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

@app.post(
    "/agent/questions",
    response_model=AgentQuestionResponse,
)
def answer_agent_question(
    request: AgentQuestionRequest,
    agent_service: Annotated[
        AgentService,
        Depends(get_agent_service),
    ],
) -> AgentQuestionResponse:
    """Interpret and execute a bounded documentation workflow."""

    result = agent_service.run_natural_language(
        question=request.question,
        product=request.product,
    )

    version_answers = []

    for item in result.version_answers:
        citations = [
            CitationResponse(
                evidence_id=citation.evidence_id,
                product=citation.product,
                version=citation.version,
                source=citation.source,
                title=citation.title,
                section=citation.section,
            )
            for citation in item.response.citations
        ]

        version_answers.append(
            VersionAnswerResponse(
                version=item.version,
                answered=item.response.answered,
                answer=item.response.answer,
                citations=citations,
            )
        )

    return AgentQuestionResponse(
        action=result.action,
        message=result.message,
        version_answers=version_answers,
    )