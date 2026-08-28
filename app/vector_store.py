from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from langsmith import traceable
from qdrant_client import QdrantClient, models

from app.models import DocumentChunk
from app.observability import (
    summarize_retrieval_inputs,
    summarize_retrieval_output,
)


DEFAULT_COLLECTION_NAME = "documentation"
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


@dataclass(frozen=True)
class RetrievalResult:
    """A retrieved chunk together with its similarity score."""

    chunk: DocumentChunk
    score: float


class VectorStore:
    """Store and retrieve versioned documentation chunks using Qdrant."""

    def __init__(
        self,
        client: QdrantClient,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    ) -> None:
        self.client = client
        self.collection_name = collection_name
        self.embedding_model = embedding_model

    def create_collection(self) -> None:
        """Create the collection and required metadata indexes."""

        if not self.client.collection_exists(
            self.collection_name
        ):
            vector_size = self.client.get_embedding_size(
                self.embedding_model
            )

            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE,
                ),
            )

        for field_name in ("product", "version"):
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name=field_name,
                field_schema=models.PayloadSchemaType.KEYWORD,
            )

    def index_chunks(
        self,
        chunks: list[DocumentChunk],
    ) -> None:
        """Embed and store document chunks with their metadata."""

        if not chunks:
            raise ValueError("At least one document chunk is required")

        self.create_collection()

        points = [
            models.PointStruct(
                id=str(
                    uuid5(
                        NAMESPACE_URL,
                        chunk.chunk_id,
                    )
                ),
                vector=models.Document(
                    text=self._embedding_text(chunk),
                    model=self.embedding_model,
                ),
                payload=self._chunk_to_payload(chunk),
            )
            for chunk in chunks
        ]

        self.client.upload_points(
            collection_name=self.collection_name,
            points=points,
        )

    @traceable(
        name="retrieval.search",
        run_type="retriever",
        process_inputs=summarize_retrieval_inputs,
        process_outputs=summarize_retrieval_output,
    )
    def search(
        self,
        query: str,
        product: str,
        version: str,
        limit: int = 3,
    ) -> list[RetrievalResult]:
        """Retrieve semantically relevant chunks from one product version."""

        if not query.strip():
            raise ValueError("Query cannot be empty")

        if not product.strip():
            raise ValueError("Product cannot be empty")

        if not version.strip():
            raise ValueError("Version cannot be empty")

        if limit < 1:
            raise ValueError("Limit must be at least 1")

        if not self.client.collection_exists(self.collection_name):
            return []

        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="product",
                    match=models.MatchValue(value=product),
                ),
                models.FieldCondition(
                    key="version",
                    match=models.MatchValue(value=version),
                ),
            ]
        )

        response = self.client.query_points(
            collection_name=self.collection_name,
            query=models.Document(
                text=query,
                model=self.embedding_model,
            ),
            query_filter=query_filter,
            with_payload=True,
            limit=limit,
        )

        return [
            RetrievalResult(
                chunk=self._payload_to_chunk(point.payload or {}),
                score=point.score,
            )
            for point in response.points
        ]

    @staticmethod
    def _embedding_text(chunk: DocumentChunk) -> str:
        """Combine the section heading and content for embedding."""

        return f"{chunk.section}\n{chunk.text}"

    @staticmethod
    def _chunk_to_payload(
        chunk: DocumentChunk,
    ) -> dict[str, str]:
        """Convert a chunk into metadata that Qdrant can store."""

        return {
            "chunk_id": chunk.chunk_id,
            "product": chunk.product,
            "version": chunk.version,
            "source": chunk.source,
            "title": chunk.title,
            "section": chunk.section,
            "text": chunk.text,
        }

    @staticmethod
    def _payload_to_chunk(
        payload: dict,
    ) -> DocumentChunk:
        """Reconstruct a DocumentChunk from a Qdrant payload."""

        required_fields = {
            "chunk_id",
            "product",
            "version",
            "source",
            "title",
            "section",
            "text",
        }

        missing_fields = required_fields - payload.keys()

        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise ValueError(
                f"Retrieved payload is missing fields: {missing}"
            )

        return DocumentChunk(
            chunk_id=str(payload["chunk_id"]),
            product=str(payload["product"]),
            version=str(payload["version"]),
            source=str(payload["source"]),
            title=str(payload["title"]),
            section=str(payload["section"]),
            text=str(payload["text"]),
        )
