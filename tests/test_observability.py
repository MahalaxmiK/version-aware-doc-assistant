from app.agent_models import AgentAction
from app.agent_service import AgentResponse, VersionAnswer
from app.generation import Evidence, GeneratedDraft
from app.observability import (
    summarize_agent_inputs,
    summarize_agent_output,
    summarize_generation_inputs,
    summarize_generation_output,
    summarize_rag_inputs,
    summarize_rag_output,
    summarize_retrieval_inputs,
    summarize_retrieval_output,
)
from app.rag_service import Citation, RAGResponse
from app.vector_store import RetrievalResult
from app.models import DocumentChunk


SECRET_QUESTION = "private customer question"
SECRET_CONTENT = "private document content"
SECRET_ANSWER = "private generated answer"


def make_rag_response() -> RAGResponse:
    evidence = Evidence(
        evidence_id="E1",
        chunk_id="chunk-1",
        product="examplecloud",
        version="v2",
        source="examplecloud/v2/api-guide.md",
        title="ExampleCloud API Guide",
        section="Authentication",
        text=SECRET_CONTENT,
        score=0.91,
    )

    return RAGResponse(
        answered=True,
        answer=SECRET_ANSWER,
        citations=(
            Citation(
                evidence_id="E1",
                product="examplecloud",
                version="v2",
                source="examplecloud/v2/api-guide.md",
                title="ExampleCloud API Guide",
                section="Authentication",
            ),
        ),
        evidence=(evidence,),
    )


def test_agent_trace_summaries_exclude_question_and_answer() -> None:
    inputs = summarize_agent_inputs(
        {
            "question": SECRET_QUESTION,
            "product": "examplecloud",
        }
    )

    output = summarize_agent_output(
        AgentResponse(
            action=AgentAction.ANSWER,
            message=None,
            version_answers=(
                VersionAnswer(
                    version="v2",
                    response=make_rag_response(),
                ),
            ),
        )
    )

    combined = repr((inputs, output))

    assert SECRET_QUESTION not in combined
    assert SECRET_ANSWER not in combined
    assert inputs["question_length"] == len(SECRET_QUESTION)
    assert output["citation_count"] == 1


def test_rag_trace_summaries_exclude_question_and_evidence() -> None:
    inputs = summarize_rag_inputs(
        {
            "question": SECRET_QUESTION,
            "product": "examplecloud",
            "version": "v2",
        }
    )
    output = summarize_rag_output(make_rag_response())
    combined = repr((inputs, output))

    assert SECRET_QUESTION not in combined
    assert SECRET_CONTENT not in combined
    assert SECRET_ANSWER not in combined
    assert output == {
        "answered": True,
        "citation_count": 1,
        "evidence_count": 1,
    }


def test_retrieval_trace_summaries_exclude_query_and_chunk_text() -> None:
    chunk = DocumentChunk(
        chunk_id="chunk-1",
        product="examplecloud",
        version="v2",
        source="examplecloud/v2/api-guide.md",
        title="ExampleCloud API Guide",
        section="Authentication",
        text=SECRET_CONTENT,
    )

    inputs = summarize_retrieval_inputs(
        {
            "query": SECRET_QUESTION,
            "product": "examplecloud",
            "version": "v2",
            "limit": 3,
        }
    )
    output = summarize_retrieval_output(
        [RetrievalResult(chunk=chunk, score=0.91234)]
    )
    combined = repr((inputs, output))

    assert SECRET_QUESTION not in combined
    assert SECRET_CONTENT not in combined
    assert output["scores"] == [0.9123]
    assert output["sections"] == ["Authentication"]


def test_generation_trace_summaries_exclude_prompts_and_answer() -> None:
    evidence = list(make_rag_response().evidence)
    inputs = summarize_generation_inputs(
        {
            "question": SECRET_QUESTION,
            "evidence": evidence,
        }
    )
    output = summarize_generation_output(
        GeneratedDraft(
            answer=SECRET_ANSWER,
            cited_evidence_ids=("E1",),
        )
    )
    combined = repr((inputs, output))

    assert SECRET_QUESTION not in combined
    assert SECRET_CONTENT not in combined
    assert SECRET_ANSWER not in combined
    assert inputs["evidence_ids"] == ["E1"]
    assert output["answer_present"] is True
