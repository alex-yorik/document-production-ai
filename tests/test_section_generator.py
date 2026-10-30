"""Offline tests for src.section_generator (no network)."""

import json

import src.section_generator as section_generator
from src.section_generator import (
    MIN_SECTION_LENGTH,
    SectionGenerator,
    _is_key_point_covered,
    validate_section,
)

OUTLINE = {
    "outline": [
        {
            "section_number": 1,
            "title": "Executive Summary",
            "description": "Overview",
            "key_points": [
                "market growth projections",
                "entry strategy options",
                "key risks assessment",
            ],
        },
        {
            "section_number": 2,
            "title": "Market Overview",
            "description": "Market size",
            "key_points": ["market size estimates"],
        },
    ]
}

COVERED_TEXT = (
    "Market growth projections and entry strategy options are discussed. "
    "This paragraph is deliberately long enough to satisfy the minimum length check. "
    "Additional qualitative analysis follows."
)


class RaisingClient:
    def __init__(self) -> None:
        self.calls = 0

    def chat_completion(self, *args, **kwargs):
        self.calls += 1
        raise RuntimeError("provider unavailable")


def test_is_key_point_covered_requires_three_tokens():
    assert _is_key_point_covered("market growth projections", "market growth") is False
    assert _is_key_point_covered("market growth projections", "market growth projections confirmed")


def test_is_key_point_covered_without_significant_tokens_is_true():
    assert _is_key_point_covered("the of and", "anything") is True
    assert _is_key_point_covered("", "anything") is True


def test_validate_section_accepts_well_formed_section():
    section = {"key_points": ["market growth projections", "entry strategy options"]}

    assert validate_section(COVERED_TEXT, section) == []


def test_validate_section_reports_empty_text():
    issues = validate_section("", {"key_points": []})

    assert "section text is empty" in issues
    assert any("section too short" in issue for issue in issues)


def test_validate_section_reports_short_text_and_missing_key_points():
    issues = validate_section("short", {"key_points": ["market growth projections"]})

    assert any("section too short" in issue for issue in issues)
    assert any(f"< {MIN_SECTION_LENGTH}" in issue for issue in issues)
    assert any("key points covered" in issue for issue in issues)


def test_generate_section_returns_client_output():
    class EchoClient:
        def chat_completion(self, *args, **kwargs):
            return "generated text"

    generator = SectionGenerator(EchoClient())
    section = OUTLINE["outline"][0]

    text = generator.generate_section(section, [{"text": "context"}], "methodology")

    assert text == "generated text"


def test_generate_all_sections_contains_client_exception(tmp_path, monkeypatch):
    draft_path = tmp_path / "draft_sections.json"
    monkeypatch.setattr(section_generator, "DRAFT_SECTIONS_PATH", draft_path)
    monkeypatch.setattr(section_generator.time, "sleep", lambda *_: None)
    client = RaisingClient()

    sections = SectionGenerator(client).generate_all_sections(OUTLINE, [{"text": "context"}], "methodology")

    assert sections == {"Executive Summary": "", "Market Overview": ""}
    assert client.calls == 2
    saved = json.loads(draft_path.read_text(encoding="utf-8"))
    assert saved == {"Executive Summary": "", "Market Overview": ""}
