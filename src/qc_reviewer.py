"""AI Quality Reviewer for generated report sections."""

import json
import logging
import re

from src.llm_client import DeepSeekClient, format_system_message, format_user_message
from src.utils import load_json, save_json

logger = logging.getLogger(__name__)

QC_TEMPERATURE = 0.2
QC_MAX_TOKENS = 2000
CHUNKS_PATH = "project_state/chunks.json"
QC_REPORT_PATH = "project_state/qc_report.json"

SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

SYSTEM_PROMPT = """
You are a strict AI Quality Reviewer for professional consulting reports.

Your task:
- Review each section for factual accuracy, methodology compliance, and quality
- Check that all claims are supported by the provided source data
- Identify hallucinations, unsupported claims, or methodology violations
- Check tone consistency (professional, data-driven, C-level appropriate)
- Verify that all key_points from the outline are covered

Return ONLY valid JSON in this format:
{
  "issues": [
    {
      "section": "Section Title",
      "issue_type": "factual_error|methodology_violation|tone_issue|missing_key_point|hallucination",
      "severity": "HIGH|MEDIUM|LOW",
      "description": "Clear description of the issue",
      "location": "Quote or reference to the problematic text",
      "suggestion": "How to fix it"
    }
  ],
  "overall_score": 85,
  "summary": "Brief summary of findings"
}

Severity rules:
- HIGH: Factual errors, hallucinations, missing critical data
- MEDIUM: Tone inconsistencies, minor methodology violations
- LOW: Style issues, minor improvements

Conciseness rules:
- Keep each issue description, location, and suggestion short (under 50 words)
- Limit the total number of issues to a maximum of 10

## Severity Calibration (with examples):

### HIGH Severity:
A number, statistic, or specific fact stated as true that does not appear anywhere in the source data.
Examples:
- "$24B market by 2029" when no such projection exists in sources
- "world's fourth most populous country" when this fact is not in source documents
- "15 million users" when source only says "large user base"

### MEDIUM Severity:
An interpretation or conclusion that is plausible but not directly stated in the sources.
Examples:
- "this suggests strong demand" when sources only give raw numbers, not analysis
- "competitive advantage" when source describes features but doesn't use this term
- "likely to succeed" when source doesn't make predictions

### LOW Severity:
A stylistic or minor phrasing issue that doesn't affect factual accuracy.
Examples:
- Inconsistent terminology (using "EdTech" and "education technology" interchangeably)
- Slightly informal tone in a professional report
- Minor grammatical issues that don't change meaning

## Rules:
- If a claim has NO support in sources → HIGH
- If a claim has PARTIAL support but goes beyond what's stated → MEDIUM
- If a claim is factually correct but poorly phrased → LOW
- When in doubt, choose MEDIUM over HIGH
"""


class QCReviewer:
    """Review generated sections against the outline and methodology."""

    def __init__(self, client: DeepSeekClient, all_chunks: list | None = None) -> None:
        self.client = client
        self.all_chunks = all_chunks

    def _ensure_chunks(self) -> None:
        """Load source chunks lazily if they were not provided."""
        if self.all_chunks is None:
            self.all_chunks = load_json(CHUNKS_PATH)
            logger.debug("Loaded %d chunks from %s", len(self.all_chunks), CHUNKS_PATH)

    def _inject_demo_issue(self, sections: dict) -> dict:
        """
        For demo: find a real problem in the generated text.
        Check for statements that lack support in the source data.
        """
        issues = []

        # Check each section for potential hallucinations
        for section_title, section_text in sections.items():
            # Look for numbers/statistics in the text
            numbers = re.findall(r"\d+\.?\d*%|\$\d+\.?\d*[BMK]?", section_text)

            # Check whether these numbers exist in the source chunks
            for number in numbers[:5]:  # Check the first 5 numbers
                found_in_source = False
                for chunk in self.all_chunks:
                    if number in chunk["text"]:
                        found_in_source = True
                        break

                if not found_in_source:
                    issues.append({
                        "section": section_title,
                        "issue_type": "potential_hallucination",
                        "severity": "HIGH",
                        "description": (
                            f"Statistic '{number}' found in text but not verified "
                            "in source documents"
                        ),
                        "location": f"Section contains: {number}",
                        "suggestion": (
                            f"Verify statistic '{number}' against source data or "
                            "mark as 'Data not available'"
                        ),
                    })
                    break  # Only one problem for the demo

        return {"issues": issues}

    def _build_messages(self, sections: dict, outline: dict, methodology_text: str) -> list[dict]:
        user_prompt = f"""
Review the following document sections against the outline and methodology.

Outline:
{json.dumps(outline, indent=2)}

Methodology:
{methodology_text}

Generated Sections:
{json.dumps(sections, indent=2)}

Be strict and thorough. Identify ALL issues, even minor ones.
"""
        return [
            format_system_message(SYSTEM_PROMPT),
            format_user_message(user_prompt),
        ]

    @staticmethod
    def _normalize_review(review) -> dict:
        if not isinstance(review, dict):
            logger.warning("QC review response is not a JSON object; using empty review")
            return {"issues": [], "overall_score": 0, "summary": "Invalid review response"}
        if not isinstance(review.get("issues"), list):
            logger.warning("QC review response has no 'issues' list; defaulting to empty")
            review["issues"] = []
        return review

    @staticmethod
    def _log_summary(review: dict) -> None:
        counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for issue in review["issues"]:
            severity = issue.get("severity")
            if severity in counts:
                counts[severity] += 1
        logger.info("QC review found %d issues", len(review["issues"]))
        logger.info("  HIGH: %d, MEDIUM: %d, LOW: %d", counts["HIGH"], counts["MEDIUM"], counts["LOW"])
        logger.info("Overall Score: %s/100", review.get("overall_score"))

    def _request_review(self, messages: list[dict]) -> dict:
        """Call the reviewer, retrying once with a larger token budget on failure."""
        try:
            return self.client.chat_completion_json(
                messages, temperature=QC_TEMPERATURE, max_tokens=QC_MAX_TOKENS
            )
        except Exception as exc:
            logger.warning(
                "QC review attempt 1 failed (%s); retrying with larger token budget", exc
            )
        return self.client.chat_completion_json(
            messages, temperature=QC_TEMPERATURE, max_tokens=QC_MAX_TOKENS * 2
        )

    def review_sections(self, sections: dict, outline: dict, methodology_text: str) -> dict:
        """Run the QC review and persist the report to project_state/qc_report.json."""
        self._ensure_chunks()

        messages = self._build_messages(sections, outline, methodology_text)
        try:
            review = self._request_review(messages)
        except Exception as exc:
            logger.error("QC review request failed: %s", exc)
            review = {
                "issues": [],
                "overall_score": 0,
                "summary": f"QC review failed: {exc}",
            }

        review = self._normalize_review(review)
        demo = self._inject_demo_issue(sections)
        review["issues"] = self._merge_issues(review.get("issues"), demo.get("issues", []))
        review["issues"].sort(key=lambda i: SEVERITY_ORDER.get(i.get("severity"), 9))

        save_json(review, QC_REPORT_PATH)
        self._log_summary(review)
        return review

    @staticmethod
    def _merge_issues(llm_issues: list, demo_issues: list) -> list:
        """Combine LLM and demo issues, dropping exact duplicates."""
        merged = list(llm_issues)
        seen = {
            (i.get("section"), i.get("description"))
            for i in merged if isinstance(i, dict)
        }
        for issue in demo_issues:
            key = (issue.get("section"), issue.get("description"))
            if key not in seen:
                merged.append(issue)
                seen.add(key)
        return merged

    def get_high_severity_issues(self, review: dict) -> list:
        """Return the list of issues with severity set to HIGH."""
        if not isinstance(review, dict):
            return []
        issues = review.get("issues")
        if not isinstance(issues, list):
            return []
        return [
            issue for issue in issues
            if isinstance(issue, dict) and issue.get("severity") == "HIGH"
        ]
