"""Revision loop: iteratively regenerate sections flagged by the QC reviewer."""

import logging

from src.llm_client import format_user_message
from src.section_generator import SECTION_MAX_TOKENS, SECTION_TEMPERATURE, SectionGenerator
from src.utils import STATE_DIR, save_json

logger = logging.getLogger(__name__)

DRAFT_SECTIONS_PATH = STATE_DIR / "draft_sections.json"

MAX_ITERATIONS = 3
ISSUE_PRIORITY = {"HIGH": 0, "MEDIUM": 1}
ACTIONABLE_SEVERITIES = ("HIGH", "MEDIUM")


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
        history: list[str] | None = None,
    ) -> dict:
        """Fix actionable issues by regenerating the affected sections.

        Issues are processed in priority order (HIGH before MEDIUM); LOW issues
        are intentionally left for human review. Sections are regenerated at
        most once per call to avoid spending iterations on duplicate issues.

        Args:
            sections: Current {title: markdown_text} map (mutated and returned).
            outline: Report outline used to look up section metadata.
            high_issues: Issues with severity HIGH or MEDIUM.
            max_attempts: Maximum regeneration attempts per issue.
            history: Summary of previous iterations added to the revision prompt.

        Returns:
            The updated sections map.
        """
        generator = SectionGenerator(self.client)
        outline_sections = {
            section.get("title"): section for section in outline.get("outline", []) if isinstance(section, dict)
        }
        fixed: set[str] = set()

        for issue in self._prioritize_issues(high_issues):
            title = issue.get("section")
            if title not in sections or title not in outline_sections:
                logger.warning("Skipping issue for unknown section: %r", title)
                continue
            if title in fixed:
                logger.debug("Section '%s' already revised, skipping duplicate issue", title)
                continue

            logger.info(
                "Revising section '%s' due to %s issue: %s",
                title,
                issue.get("severity"),
                issue.get("description"),
            )
            if self._revise_section(generator, sections, outline_sections[title], issue, max_attempts, history):
                fixed.add(title)

        logger.info("Revision complete. Fixed %d section(s).", len(fixed))
        return sections

    @staticmethod
    def _prioritize_issues(issues: list) -> list:
        """Return actionable issues sorted HIGH → MEDIUM, dropping LOW and junk."""
        actionable = [
            issue
            for issue in issues
            if isinstance(issue, dict) and issue.get("severity") in ACTIONABLE_SEVERITIES
        ]
        return sorted(actionable, key=lambda issue: ISSUE_PRIORITY.get(issue.get("severity"), 9))

    @staticmethod
    def _review_issues(review: dict) -> list:
        """Return the issue list from a review dict, tolerating malformed input."""
        issues = review.get("issues") if isinstance(review, dict) else None
        return issues if isinstance(issues, list) else []

    def run(
        self,
        sections: dict,
        outline: dict,
        initial_review: dict,
        qc_review,
        max_iterations: int = MAX_ITERATIONS,
    ) -> tuple[dict, dict, dict]:
        """Revise and re-review until issues stop decreasing.

        Args:
            sections: Current {title: markdown_text} map.
            outline: Report outline used to look up section metadata.
            initial_review: QC review produced before the loop.
            qc_review: Callable ``(sections) -> review dict`` used for intermediate checks.
            max_iterations: Hard cap on revision passes.

        Returns:
            ``(sections, last_review, metrics)`` where metrics contains
            ``revision_iterations``, ``issues_per_iteration`` and
            ``convergence_status`` (reached / max_iterations / regression).
        """
        current_review = initial_review if isinstance(initial_review, dict) else {"issues": []}
        previous_total = len(self._review_issues(current_review))
        trajectory = [previous_total]
        actionable = self._prioritize_issues(self._review_issues(current_review))
        history: list[str] = []
        iterations = 0
        status = "reached"

        for iteration in range(1, max_iterations + 1):
            if not actionable:
                break

            iterations = iteration
            sections = self.fix_sections(sections, outline, actionable, history=history)
            review = qc_review(sections)
            if not isinstance(review, dict):
                logger.warning("Intermediate QC returned %r; treating as no issues", type(review).__name__)
                review = {"issues": []}

            total = len(self._review_issues(review))
            trajectory.append(total)
            improvement = previous_total - total
            logger.info(
                "Iteration %d: issues %d→%d (improvement %d)",
                iteration,
                previous_total,
                total,
                improvement,
            )
            current_review = review

            if total < previous_total:
                previous_total = total
                actionable = self._prioritize_issues(self._review_issues(review))
                history.append(f"Iteration {iteration}: issues {trajectory[-2]}→{total}")
                if not actionable:
                    status = "reached"
                    break
                continue

            status = "regression" if total > previous_total else "reached"
            break
        else:
            status = "max_iterations"
            if not actionable:
                status = "reached"

        metrics = {
            "revision_iterations": iterations,
            "issues_per_iteration": trajectory,
            "convergence_status": status,
        }
        return sections, current_review, metrics

    def _revise_section(
        self,
        generator: SectionGenerator,
        sections: dict,
        section_meta: dict,
        issue: dict,
        max_attempts: int,
        history: list[str] | None = None,
    ) -> bool:
        """Regenerate one section with QC feedback appended; returns True on success."""
        context_lines = [
            f"CRITICAL FEEDBACK FROM QC REVIEWER: {issue.get('description', '')}.",
            f"Please fix this issue: {issue.get('suggestion', '')}",
            "Fix only the flagged issues and do not add new unsupported claims "
            "(не добавляй новые claims).",
            "Preserve facts from the source documents and do not invent data "
            "(сохраняй факты из source documents).",
        ]
        if history:
            context_lines.append("Previous revision history: " + " | ".join(history))
        feedback = " ".join(context_lines)
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
