"""Simple keyword-based retrieval over ingested document chunks."""

import logging
import re
from typing import Any

from src.utils import STATE_DIR, load_json

logger = logging.getLogger(__name__)

CHUNKS_PATH = STATE_DIR / "chunks.json"


def load_chunks() -> list[dict[str, Any]]:
    """Load chunk records from the project state file."""
    chunks = load_json(CHUNKS_PATH)
    if not isinstance(chunks, list):
        raise ValueError(f"Expected a JSON list in {CHUNKS_PATH}, got {type(chunks).__name__}")
    logger.info("Loaded %d chunks from %s", len(chunks), CHUNKS_PATH)
    return chunks


def _tokenize(text: str) -> list[str]:
    """Split text into lowercase alphanumeric tokens."""
    return re.findall(r"[a-z0-9]+", text.lower())


def keyword_search(
    query: str,
    chunks: list[dict[str, Any]],
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """Rank chunks by count of query tokens present in their text.

    Args:
        query: Search query.
        chunks: List of chunk records with a "text" key.
        top_k: Number of top results to return.

    Returns:
        Up to top_k chunks, best-scoring first. If all scores are zero the
        first top_k chunks are still returned.
    """
    query_tokens = set(_tokenize(query))

    def score(chunk: dict[str, Any]) -> int:
        text_tokens = set(_tokenize(chunk["text"]))
        return len(query_tokens & text_tokens)

    ranked = sorted(chunks, key=score, reverse=True)
    return ranked[:top_k]


def get_relevant_chunks_for_section(
    section_title: str,
    chunks: list[dict[str, Any]],
    top_k: int = 3,
) -> list[str]:
    """Return the text of the most relevant chunks for a section title.

    Args:
        section_title: Report section title used as the search query.
        chunks: List of chunk records.
        top_k: Number of chunks to retrieve.

    Returns:
        List of chunk texts, best match first.
    """
    query = re.sub(r"[^a-zA-Z0-9\s]", " ", section_title).strip()
    results = keyword_search(query, chunks, top_k=top_k)
    return [chunk["text"] for chunk in results]


def format_context(chunks_texts: list[str]) -> str:
    """Join chunk texts into a single prompt context block.

    Args:
        chunks_texts: List of chunk texts.

    Returns:
        Context string prefixed with "Relevant context:".
    """
    return "Relevant context:\n" + "\n\n---\n\n".join(chunks_texts)
