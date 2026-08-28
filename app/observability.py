"""Privacy-conscious summaries used by optional LangSmith tracing."""

from typing import Any


def summarize_agent_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    """Describe an agent request without recording its raw question."""

    question = str(inputs.get("question", ""))

    return {
        "product": inputs.get("product"),
        "question_length": len(question),
    }


def summarize_agent_output(output: Any) -> dict[str, Any]:
    """Record routing and grounding outcomes without answer text."""

    version_answers = tuple(
        getattr(output, "version_answers", ())
    )

    return {
        "action": getattr(
            getattr(output, "action", None),
            "value",
            None,
        ),
        "versions": [
            item.version for item in version_answers
        ],
        "answered_versions": sum(
            item.response.answered for item in version_answers
        ),
        "citation_count": sum(
            len(item.response.citations)
            for item in version_answers
        ),
    }


def summarize_intent_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    """Describe intent interpretation without logging the question."""

    question = str(inputs.get("question", ""))

    return {
        "product": inputs.get("product"),
        "available_versions": list(
            inputs.get("available_versions", ())
        ),
        "question_length": len(question),
    }


def summarize_intent_output(output: Any) -> dict[str, Any]:
    """Record the interpreted route without the rewritten question."""

    focused_question = str(
        getattr(output, "focused_question", "")
    )

    return {
        "requested_versions": list(
            getattr(output, "requested_versions", ())
        ),
        "comparison_requested": bool(
            getattr(output, "comparison_requested", False)
        ),
        "focused_question_length": len(focused_question),
    }


def summarize_rag_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    """Describe a scoped RAG request without its raw question."""

    question = str(inputs.get("question", ""))

    return {
        "product": inputs.get("product"),
        "version": inputs.get("version"),
        "question_length": len(question),
    }


def summarize_rag_output(output: Any) -> dict[str, Any]:
    """Record grounding outcomes without answer or evidence text."""

    return {
        "answered": bool(getattr(output, "answered", False)),
        "citation_count": len(
            getattr(output, "citations", ())
        ),
        "evidence_count": len(
            getattr(output, "evidence", ())
        ),
    }


def summarize_retrieval_inputs(
    inputs: dict[str, Any],
) -> dict[str, Any]:
    """Describe a filtered search without recording its raw query."""

    query = str(inputs.get("query", ""))

    return {
        "product": inputs.get("product"),
        "version": inputs.get("version"),
        "limit": inputs.get("limit", 3),
        "query_length": len(query),
    }


def summarize_retrieval_output(output: Any) -> dict[str, Any]:
    """Record retrieval volume and scores without document content."""

    results = list(output or [])

    return {
        "result_count": len(results),
        "scores": [round(result.score, 4) for result in results],
        "sections": [result.chunk.section for result in results],
    }


def summarize_generation_inputs(
    inputs: dict[str, Any],
) -> dict[str, Any]:
    """Describe generation context without prompts or evidence text."""

    question = str(inputs.get("question", ""))
    evidence = list(inputs.get("evidence", ()))

    return {
        "question_length": len(question),
        "evidence_count": len(evidence),
        "evidence_ids": [item.evidence_id for item in evidence],
        "products": sorted({item.product for item in evidence}),
        "versions": sorted({item.version for item in evidence}),
    }


def summarize_generation_output(output: Any) -> dict[str, Any]:
    """Record structured generation outcomes without answer text."""

    return {
        "answer_present": bool(
            str(getattr(output, "answer", "")).strip()
        ),
        "cited_evidence_ids": list(
            getattr(output, "cited_evidence_ids", ())
        ),
    }
