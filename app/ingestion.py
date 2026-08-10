import hashlib
import re
from pathlib import Path

from app.models import DocumentChunk


H1_PATTERN = re.compile(r"^#\s+(.+?)\s*$")
H2_PATTERN = re.compile(r"^##\s+(.+?)\s*$")


def create_chunk_id(
    product: str,
    version: str,
    source: str,
    section: str,
) -> str:
    """Create a stable identifier from a chunk's metadata."""

    value = f"{product}|{version}|{source}|{section}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def parse_markdown_file(
    file_path: Path,
    data_root: Path,
) -> list[DocumentChunk]:
    """Convert the level-two sections of one Markdown file into chunks."""

    relative_path = file_path.relative_to(data_root)
    path_parts = relative_path.parts

    if len(path_parts) < 3:
        raise ValueError(
            "Expected document path in the format "
            "'<product>/<version>/<filename>.md'"
        )

    product = path_parts[0]
    version = path_parts[1]
    source = relative_path.as_posix()

    lines = file_path.read_text(encoding="utf-8").splitlines()

    title = file_path.stem
    current_section: str | None = None
    current_content: list[str] = []
    chunks: list[DocumentChunk] = []

    def save_current_section() -> None:
        if current_section is None:
            return

        text = "\n".join(current_content).strip()

        if not text:
            return

        chunk_id = create_chunk_id(
            product=product,
            version=version,
            source=source,
            section=current_section,
        )

        chunks.append(
            DocumentChunk(
                chunk_id=chunk_id,
                product=product,
                version=version,
                source=source,
                title=title,
                section=current_section,
                text=text,
            )
        )

    for line in lines:
        h1_match = H1_PATTERN.match(line)

        if h1_match:
            title = h1_match.group(1).strip()
            continue

        h2_match = H2_PATTERN.match(line)

        if h2_match:
            save_current_section()
            current_section = h2_match.group(1).strip()
            current_content = []
            continue

        if current_section is not None:
            current_content.append(line)

    save_current_section()

    return chunks


def load_document_chunks(data_root: Path) -> list[DocumentChunk]:
    """Load every Markdown document underneath the data directory."""

    if not data_root.exists():
        raise FileNotFoundError(f"Data directory not found: {data_root}")

    chunks: list[DocumentChunk] = []

    for file_path in sorted(data_root.rglob("*.md")):
        chunks.extend(
            parse_markdown_file(
                file_path=file_path,
                data_root=data_root,
            )
        )

    return chunks