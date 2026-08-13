from functools import lru_cache
from pathlib import Path

from qdrant_client import QdrantClient

from app.ingestion import load_document_chunks
from app.openai_generator import OpenAIAnswerGenerator
from app.rag_service import RAGService
from app.vector_store import VectorStore

from app.agent_router import AgentRouter
from app.agent_service import AgentService
from app.intent_interpreter import OpenAIIntentInterpreter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data"


@lru_cache(maxsize=1)
def get_rag_service() -> RAGService:
    """Initialize and cache the complete RAG service."""

    chunks = load_document_chunks(DATA_ROOT)

    qdrant_client = QdrantClient(":memory:")

    vector_store = VectorStore(
        client=qdrant_client,
    )

    vector_store.index_chunks(chunks)

    answer_generator = OpenAIAnswerGenerator()

    return RAGService(
        vector_store=vector_store,
        answer_generator=answer_generator,
    )

@lru_cache(maxsize=1)
def get_agent_service() -> AgentService:
    """Initialize and cache the bounded agent service."""

    chunks = load_document_chunks(DATA_ROOT)

    versions_by_product: dict[str, list[str]] = {}

    for chunk in chunks:
        product_versions = versions_by_product.setdefault(
            chunk.product,
            [],
        )

        if chunk.version not in product_versions:
            product_versions.append(chunk.version)

    router = AgentRouter(
        available_versions=versions_by_product,
    )

    return AgentService(
        router=router,
        rag_service=get_rag_service(),
        intent_interpreter=OpenAIIntentInterpreter(),
    )