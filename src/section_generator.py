"""Section generation using the LLM client and retrieval over source chunks."""

import logging
import re
import time

from src.llm_client import DeepSeekClient, format_system_message, format_user_message
from src.retrieval import format_context, get_relevant_chunks_for_section
from src.utils import STATE_DIR, save_json

logger = logging.getLogger(__name__)

SECTION_TEMPERATURE = 0.7
SECTION_MAX_TOKENS = 2000
MIN_SECTION_LENGTH = 100
MIN_COVERED_KEY_POINTS = 2
RATE_LIMIT_DELAY_SECONDS = 1.5

DRAFT_SECTIONS_PATH = STATE_DIR / "draft_sections.json"

STOPWORDS = {
    "the",
    "a",
    "an",
    "of",
    "in",
    "to",
    "and",
    "for",
    "on",
    "with",
    "as",
    "by",
    "at",
    "from",
    "is",
    "are",
    "it",
    "its",
    "this",
    "that",
    "was",
    "were",
    "be",
    "will",
    "or",
    "but",
    "not",
    "their",
    "they",
    "over",
    "up",
    "down",
    "out",
    "about",
    "than",
    "then",
    "them",
    "into",
    "has",
    "have",
    "had",
    "do",
    "does",
    "did",
    "can",
    "could",
    "should",
    "may",
    "might",
}


def _tokenize(text: str) -> set[str]:
    """Return lowercase alphanumeric tokens from text, excluding stopwords."""
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if token not in STOPWORDS}


def _is_key_point_covered(key_point: str, text: str) -> bool:
    """Return True when enough significant tokens of a key point appear in text."""
    point_tokens = _tokenize(key_point)
    if not point_tokens:
        return True
    matches = point_tokens & _tokenize(text)
    return len(matches) >= 3


def validate_section(text: str, section: dict) -> list[str]:
    """Check a generated section against minimal content requirements.

    Returns:
        A list of human-readable issues; empty when the section is acceptable.
    """
    issues: list[str] = []
    if not text.strip():
        issues.append("section text is empty")
    if len(text) < MIN_SECTION_LENGTH:
        issues.append(f"section too short: {len(text)} chars < {MIN_SECTION_LENGTH}")
    key_points = section.get("key_points") or []
    covered = sum(1 for point in key_points if _is_key_point_covered(point, text))
    if covered < MIN_COVERED_KEY_POINTS:
        issues.append(f"only {covered} of {len(key_points)} key points covered (need >= {MIN_COVERED_KEY_POINTS})")
    return issues


class SectionGenerator:
    """Write report sections via the LLM using retrieval-backed context."""

    def __init__(self, client: DeepSeekClient) -> None:
        self.client = client

    def _build_messages(self, section: dict, all_chunks: list, methodology_text: str) -> list[dict[str, str]]:
        system_prompt = f"""
You are a professional consultant writing a section of a market entry report.

Your task:
- Write a detailed, professional section based on the provided context
- Follow the company methodology strictly
- Use ONLY facts from the provided context — do NOT hallucinate
- If data is missing, explicitly state "Data not available"
- Tone: professional, data-driven, accessible to C-level executives
- Length: approximately {len(section["key_points"]) * 200} words

Structure the section with:
- Clear introduction
- Data-backed analysis
- Specific examples and numbers from the context
- Actionable insights
"""
        user_prompt = f"""
Section to write: {section["title"]}
Description: {section["description"]}
Key points to cover:
{chr(10).join(f"• {point}" for point in section["key_points"])}

Company Methodology:
{methodology_text}

Relevant Context from source documents:
{format_context(get_relevant_chunks_for_section(section["title"], all_chunks))}

Write the complete section following the methodology and covering all key points.
Use markdown formatting (headers, lists, bold for key numbers).
"""
        return [
            format_system_message(system_prompt),
            format_user_message(user_prompt),
        ]

    def generate_section(self, section: dict, all_chunks: list, methodology_text: str) -> str:
        """Generate the text of one section and log time and token estimate."""
        messages = self._build_messages(section, all_chunks, methodology_text)
        started_at = time.monotonic()
        text = self.client.chat_completion(
            messages,
            temperature=SECTION_TEMPERATURE,
            max_tokens=SECTION_MAX_TOKENS,
        )
        elapsed = time.monotonic() - started_at
        estimated_tokens = len(text) // 4
        logger.info(
            "Section '%s' generated in %.2fs (~%d estimated tokens, %d chars)",
            section["title"],
            elapsed,
            estimated_tokens,
            len(text),
        )
        return text

    def _save_draft(self, sections: dict[str, str]) -> None:
        save_json(sections, DRAFT_SECTIONS_PATH)
        logger.debug("Saved draft sections (%d) to %s", len(sections), DRAFT_SECTIONS_PATH)

    def generate_all_sections(self, outline: dict, all_chunks: list, methodology_text: str) -> dict[str, str]:
        """Generate every outline section, validating and persisting after each."""
        sections: dict[str, str] = {}
        outline_sections = outline.get("outline", [])
        for idx, section in enumerate(outline_sections):
            title = section.get("title", f"Section {idx + 1}")
            number = section.get("section_number", idx + 1)
            logger.info("Generating section %s: %s", number, title)
            try:
                text = self.generate_section(section, all_chunks, methodology_text)
            except Exception as exc:  # noqa: BLE001 — one failed section must not abort the report
                logger.error("Failed to generate section '%s': %s", title, exc)
                sections[title] = ""
                self._save_draft(sections)
                continue
            sections[title] = text
            for issue in validate_section(text, section):
                logger.warning("Validation warning for section '%s': %s", title, issue)
            self._save_draft(sections)
            if idx < len(outline_sections) - 1:
                time.sleep(RATE_LIMIT_DELAY_SECONDS)
        return sections
