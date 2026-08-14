import os
from functools import lru_cache
from pathlib import Path

from qdrant_client import QdrantClient

from app.agent_router import AgentRouter
from app.agent_service import AgentService
from app.ingestion import load_document_chunks
from app.intent_interpreter import OpenAIIntentInterpreter
from app.openai_generator import OpenAIAnswerGenerator
from app.rag_service import RAGService
from app.vector_store import (
    DEFAULT_COLLECTION_NAME,
    VectorStore,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data"
DEFAULT_QDRANT_PATH = PROJECT_ROOT / "vector_store"


def create_qdrant_client() -> QdrantClient:
    """Create a cloud or locally persistent Qdrant client."""

    qdrant_url = os.getenv("QDRANT_URL", "").strip()
    qdrant_api_key = os.getenv(
        "QDRANT_API_KEY",
        "",
    ).strip()

    if bool(qdrant_url) != bool(qdrant_api_key):
        raise ValueError(
            "QDRANT_URL and QDRANT_API_KEY must be "
            "configured together"
        )

    if qdrant_url:
        return QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key,
            timeout=60,
        )

    local_path = Path(
        os.getenv(
            "QDRANT_PATH",
            str(DEFAULT_QDRANT_PATH),
        )
    )

    return QdrantClient(path=str(local_path))


@lru_cache(maxsize=1)
def get_rag_service() -> RAGService:
    """Initialize and cache the complete RAG service."""

    chunks = load_document_chunks(DATA_ROOT)

    vector_store = VectorStore(
        client=create_qdrant_client(),
        collection_name=os.getenv(
            "QDRANT_COLLECTION_NAME",
            DEFAULT_COLLECTION_NAME,
        ),
    )

    # Stable IDs make repeated startup indexing an idempotent upsert.
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