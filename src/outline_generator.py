"""Outline generation for the market entry report from brief, methodology and market data."""

import json
import logging

from run_pipeline import REQUIRED_INPUT_FILES
from src.llm_client import DeepSeekClient, format_system_message, format_user_message
from src.utils import INPUT_DIR, STATE_DIR, save_json

logger = logging.getLogger(__name__)

OUTLINE_PATH = STATE_DIR / "outline.json"
OUTLINE_RAW_PATH = STATE_DIR / "outline_raw_response.txt"

OUTLINE_TEMPERATURE = 0.3
OUTLINE_MAX_TOKENS = 1500
MAX_ATTEMPTS = 2

REQUIRED_SECTIONS = (
    "Executive Summary",
    "Market Overview",
    "Competitive Landscape",
    "Key Risks",
    "Recommendations",
)

SYSTEM_PROMPT = """
You are an expert consultant creating a structured outline for a market entry report.

Your task:
- Create a detailed JSON outline with 5-6 sections
- Each section must have: title, description, key_points (3-5 bullets)
- Follow the methodology guidelines strictly
- Base the outline on the provided brief and market data

Required sections (adapt titles as needed):
1. Executive Summary
2. Market Overview
3. Competitive Landscape
4. Key Risks
5. Recommendations

Return ONLY valid JSON in this format:
{
  "outline": [
    {
      "section_number": 1,
      "title": "Executive Summary",
      "description": "Brief overview...",
      "key_points": ["Point 1", "Point 2", "Point 3"],
      "estimated_length": "1-2 pages"
    }
  ],
  "total_estimated_pages": 5
}
"""


class OutlineGenerator:
    """Build a report outline via the LLM client and persist it to project_state."""

    def __init__(self, client: DeepSeekClient) -> None:
        self.client = client

    def _build_messages(
        self,
        brief_text: str,
        methodology_text: str,
        market_data_text: str,
    ) -> list[dict[str, str]]:
        user_prompt = f"""
Company Brief:
{brief_text}

Methodology:
{methodology_text}

Market Data:
{market_data_text}

Generate the outline following the methodology and brief requirements.
"""
        return [
            format_system_message(SYSTEM_PROMPT),
            format_user_message(user_prompt),
        ]

    def _save_raw_response(self, data: dict) -> None:
        raw_text = json.dumps(data, ensure_ascii=False, indent=2)
        OUTLINE_RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTLINE_RAW_PATH.write_text(raw_text, encoding="utf-8")
        logger.debug("Saved raw outline response to %s", OUTLINE_RAW_PATH)

    def _validate_structure(self, data: dict | list) -> bool:
        if not isinstance(data, dict):
            logger.warning("Outline validation: response is not a JSON object")
            return False
        outline = data.get("outline")
        if not isinstance(outline, list):
            logger.warning("Outline validation: 'outline' key missing or not a list")
            return False
        return True

    def _validate_sections(self, data: dict) -> None:
        sections = data.get("outline", [])
        titles = [s.get("title", "") for s in sections if isinstance(s, dict)]
        for required in REQUIRED_SECTIONS:
            if not any(required.lower() in title.lower() for title in titles):
                logger.warning("Outline validation: required section missing: %s", required)
        for idx, section in enumerate(sections, start=1):
            if not isinstance(section, dict):
                logger.warning("Outline validation: section %d is not an object", idx)
                continue
            for field in ("title", "description"):
                if not section.get(field):
                    logger.warning(
                        "Outline validation: section %d (%s) missing '%s'",
                        idx,
                        section.get("title") or "untitled",
                        field,
                    )
            key_points = section.get("key_points")
            if not isinstance(key_points, list) or not 3 <= len(key_points) <= 5:
                logger.warning(
                    "Outline validation: section %d key_points must be a 3-5 item list, got %r",
                    idx,
                    key_points,
                )

    def generate_outline(
        self,
        brief_text: str,
        methodology_text: str,
        market_data_text: str,
    ) -> dict:
        """Generate, validate and persist the report outline.

        Retries once if the LLM returns invalid JSON or a malformed structure.

        Returns:
            The validated outline dict with an "outline" list of sections.

        Raises:
            RuntimeError: If all attempts fail.
        """
        messages = self._build_messages(brief_text, methodology_text, market_data_text)
        last_error: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                data = self.client.chat_completion_json(
                    messages,
                    temperature=OUTLINE_TEMPERATURE,
                    max_tokens=OUTLINE_MAX_TOKENS,
                )
                self._save_raw_response(data)
                if not self._validate_structure(data):
                    raise ValueError(
                        "LLM response has no 'outline' key or it is not a list"
                    )
                save_json(data, OUTLINE_PATH)
                self._validate_sections(data)
                logger.info("Generated outline with %d sections", len(data["outline"]))
                return data
            except (ValueError, json.JSONDecodeError) as exc:
                last_error = exc
                logger.warning(
                    "Outline generation attempt %d/%d failed: %s",
                    attempt,
                    MAX_ATTEMPTS,
                    exc,
                )
        raise RuntimeError(
            f"Outline generation failed after {MAX_ATTEMPTS} attempts: {last_error}"
        )


def load_input_files() -> tuple[str, str, str]:
    """Read the three input documents used for outline generation.

    Returns:
        Tuple of (company_brief, methodology, market_data) texts.

    Raises:
        ValueError: If a required input file is missing or cannot be read.
    """
    texts: list[str] = []
    for filename in REQUIRED_INPUT_FILES:
        path = INPUT_DIR / filename
        try:
            texts.append(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError) as exc:
            raise ValueError(
                f"Could not read required input file '{filename}' ({path}): {exc}"
            ) from exc
    return texts[0], texts[1], texts[2]
