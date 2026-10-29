"""Ingestion stage: read input documents, chunk them, persist metadata."""

import logging
from pathlib import Path
from typing import Any

from src.utils import INPUT_DIR, STATE_DIR, ensure_directories, save_json

SUPPORTED_EXTENSIONS = {".md", ".txt"}

CHUNKS_OUTPUT = STATE_DIR / "chunks.json"

logger = logging.getLogger(__name__)


def read_file(file_path: str | Path) -> str:
    """Read a .md or .txt file and return its text content.

    Args:
        file_path: Path to the input file.

    Returns:
        Full text content of the file.

    Raises:
        ValueError: If the file extension is not supported.
    """
    path = Path(file_path)
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file extension '{path.suffix}' for {path.name}; supported: {sorted(SUPPORTED_EXTENSIONS)}"
        )
    return path.read_text(encoding="utf-8")


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks of roughly equal length.

    Args:
        text: Source text to split.
        chunk_size: Maximum number of characters per chunk.
        overlap: Number of characters of overlap between adjacent chunks.

    Returns:
        List of chunk strings.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be in range [0, chunk_size)")

    normalized = text.replace("\r\n", "\n")
    length = len(normalized)
    if length <= chunk_size:
        return [normalized]

    chunks: list[str] = []
    start = 0
    step = chunk_size - overlap
    while start < length:
        end = start + chunk_size
        chunks.append(normalized[start:end])
        if end >= length:
            break
        start += step
    return chunks


def process_documents(chunk_size: int = 500, overlap: int = 50) -> list[dict[str, Any]]:
    """Read all supported files from input/, chunk them, and persist results.

    Args:
        chunk_size: Character size of each chunk.
        overlap: Character overlap between adjacent chunks.

    Returns:
        List of chunk records, each with source_file, chunk_index and text.
    """
    ensure_directories()
    chunks: list[dict[str, Any]] = []
    processed_files = 0

    if not INPUT_DIR.exists() or not INPUT_DIR.is_dir():
        logger.warning("Input directory %s not found; nothing to process", INPUT_DIR)
        save_json(chunks, CHUNKS_OUTPUT)
        return chunks

    for file_path in sorted(INPUT_DIR.iterdir()):
        if not file_path.is_file() or file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        try:
            text = read_file(file_path)
        except (OSError, ValueError) as exc:
            logger.error("Skipping %s: %s", file_path.name, exc)
            continue
        processed_files += 1
        file_chunks = chunk_text(text, chunk_size, overlap)
        for index, chunk_text_value in enumerate(file_chunks):
            chunks.append(
                {
                    "source_file": file_path.name,
                    "chunk_index": index,
                    "text": chunk_text_value,
                }
            )
        logger.info("Ingested %s -> %d chunks", file_path.name, len(file_chunks))

    save_json(chunks, CHUNKS_OUTPUT)
    logger.info(
        "Ingestion done: %d files processed, %d chunks written to %s",
        processed_files,
        len(chunks),
        CHUNKS_OUTPUT,
    )
    return chunks
