"""Revision loop: regenerate sections flagged with HIGH severity issues."""

import logging

from src.llm_client import format_user_message
from src.section_generator import SECTION_MAX_TOKENS, SECTION_TEMPERATURE, SectionGenerator
from src.utils import STATE_DIR, save_json

logger = logging.getLogger(__name__)

DRAFT_SECTIONS_PATH = STATE_DIR / "draft_sections.json"


class RevisionLoop:
    """Re-generate failing sections by feeding QC feedback back to the generator."""

    def __init__(
        self,
        client,
        all_chunks: list,
        methodology_text: str,
    ) -> None:
        self.client = client
        self.all_chunks = all_chunks
        self.methodology_text = methodology_text

    def fix_sections(
        self,
        sections: dict,
        outline: dict,
        high_issues: list,
        max_attempts: int = 2,
    ) -> dict:
        """Fix every HIGH issue by regenerating the affected section.

        Args:
            sections: Current {title: markdown_text} map (mutated and returned).
            outline: Report outline used to look up section metadata.
            high_issues: Issues with severity == "HIGH".
            max_attempts: Maximum regeneration attempts per issue.

        Returns:
            The updated sections map.
        """
        generator = SectionGenerator(self.client)
        outline_sections = {
            section.get("title"): section for section in outline.get("outline", []) if isinstance(section, dict)
        }
        fixed: set[str] = set()

        for issue in high_issues:
            if not isinstance(issue, dict):
                continue
            title = issue.get("section")
            if title not in sections or title not in outline_sections:
                logger.warning("Skipping issue for unknown section: %r", title)
                continue
            if title in fixed:
                logger.debug("Section '%s' already revised, skipping duplicate issue", title)
                continue

            logger.info("Revising section '%s' due to HIGH issue: %s", title, issue.get("description"))
            if self._revise_section(generator, sections, outline_sections[title], issue, max_attempts):
                fixed.add(title)

        logger.info("Revision complete. Fixed %d section(s).", len(fixed))
        return sections

    def _revise_section(
        self,
        generator: SectionGenerator,
        sections: dict,
        section_meta: dict,
        issue: dict,
        max_attempts: int,
    ) -> bool:
        """Regenerate one section with QC feedback appended; returns True on success."""
        feedback = (
            f"CRITICAL FEEDBACK FROM QC REVIEWER: {issue.get('description', '')}. "
            f"Please fix this issue: {issue.get('suggestion', '')}"
        )
        title = issue.get("section")

        for attempt in range(1, max_attempts + 1):
            messages = generator._build_messages(section_meta, self.all_chunks, self.methodology_text)
            messages.append(format_user_message(feedback))
            try:
                new_text = self.client.chat_completion(
                    messages,
                    temperature=SECTION_TEMPERATURE,
                    max_tokens=SECTION_MAX_TOKENS,
                )
            except Exception as exc:  # noqa: BLE001 — a failed attempt must not abort remaining sections
                logger.error(
                    "Revision attempt %d/%d for '%s' failed: %s",
                    attempt,
                    max_attempts,
                    title,
                    exc,
                )
                continue

            if new_text.strip():
                sections[title] = new_text
                save_json(sections, DRAFT_SECTIONS_PATH)
                logger.info("Section '%s' revised successfully on attempt %d", title, attempt)
                return True
            logger.warning(
                "Revision attempt %d/%d for '%s' returned empty text",
                attempt,
                max_attempts,
                title,
            )
        return False
