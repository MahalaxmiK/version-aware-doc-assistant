from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentChunk:
    """A searchable section extracted from a source document."""

    chunk_id: str
    product: str
    version: str
    source: str
    title: str
    section: str
    text: str