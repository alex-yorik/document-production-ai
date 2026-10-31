"""Shared offline fixtures: deterministic FakeClient and isolated pipeline paths."""

import copy
from pathlib import Path

import pytest

import run_pipeline
import src.document_assembler as document_assembler
import src.ingestion as ingestion
import src.outline_generator as outline_generator
import src.qc_reviewer as qc_reviewer
import src.retrieval as retrieval
import src.revision_loop as revision_loop
import src.section_generator as section_generator

DEMO_INPUT_DIR = Path(__file__).resolve().parent.parent / "demo" / "input"

OUTLINE = {
    "outline": [
        {
            "section_number": 1,
            "title": "Executive Summary",
            "description": "Brief overview of the market entry.",
            "key_points": [
                "market growth projections",
                "entry strategy options",
                "key risks assessment",
            ],
            "estimated_length": "1-2 pages",
        },
        {
            "section_number": 2,
            "title": "Market Overview",
            "description": "Market size and dynamics.",
            "key_points": [
                "market size estimates",
                "growth drivers analysis",
                "competitive pressure overview",
            ],
            "estimated_length": "2 pages",
        },
    ],
    "total_estimated_pages": 4,
}

SECTION_TEXT = (
    "## Section\n\n"
    "Market growth projections, entry strategy options and key risks assessment "
    "are covered together with market size estimates, growth drivers analysis and "
    "competitive pressure overview. This section contains no numeric statistics, "
    "so the automated traceability check stays clean. " + "Detailed qualitative analysis follows. " * 5
)

HIGH_ISSUE = {
    "section": "Executive Summary",
    "issue_type": "factual_error",
    "severity": "HIGH",
    "description": "Unsupported claim about market leadership.",
    "location": "Executive Summary paragraph 2",
    "suggestion": "Remove the claim or add source support.",
}


class FakeClient:
    """Deterministic stand-in for LLMClient covering every pipeline stage."""

    def __init__(self, *, high_issues: bool = True, qc_raises: bool = False) -> None:
        self.high_issues = high_issues
        self.qc_raises = qc_raises
        self.qc_calls = 0
        self.revision_calls = 0

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        content = "\n".join(message.get("content", "") for message in messages)
        if "CRITICAL FEEDBACK FROM QC REVIEWER" in content:
            self.revision_calls += 1
        return SECTION_TEXT

    def chat_completion_json(
        self,
        messages: list[dict[str, str]],
        schema_description: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2000,
    ) -> dict:
        if max_tokens <= 1500:
            return copy.deepcopy(OUTLINE)
        if self.qc_raises:
            raise RuntimeError("QC service unavailable")
        self.qc_calls += 1
        return self._qc_report(is_draft=self.qc_calls == 1)

    def _qc_report(self, *, is_draft: bool) -> dict:
        if is_draft and self.high_issues:
            return {
                "issues": [copy.deepcopy(HIGH_ISSUE)],
                "overall_score": 60,
                "summary": "Draft review with one HIGH issue.",
            }
        if is_draft:
            return {
                "issues": [],
                "overall_score": 80,
                "summary": "Draft review with no issues.",
            }
        return {
            "issues": [],
            "overall_score": 90 if self.high_issues else 80,
            "summary": "Final review with no issues.",
        }


@pytest.fixture
def fake_client_class() -> type[FakeClient]:
    return FakeClient


@pytest.fixture
def offline_env(monkeypatch, tmp_path) -> dict[str, Path]:
    """Point every module-level path at tmp dirs; demo input stays read-only."""
    state_dir = tmp_path / "state"
    output_dir = tmp_path / "output"
    state_dir.mkdir()
    output_dir.mkdir()

    monkeypatch.setattr(run_pipeline, "INPUT_DIR", DEMO_INPUT_DIR)
    monkeypatch.setattr(run_pipeline, "STATE_DIR", state_dir)
    monkeypatch.setattr(run_pipeline, "CHUNKS_PATH", state_dir / "chunks.json")

    monkeypatch.setattr(ingestion, "INPUT_DIR", DEMO_INPUT_DIR)
    monkeypatch.setattr(ingestion, "STATE_DIR", state_dir)
    monkeypatch.setattr(ingestion, "CHUNKS_OUTPUT", state_dir / "chunks.json")

    monkeypatch.setattr(outline_generator, "INPUT_DIR", DEMO_INPUT_DIR)
    monkeypatch.setattr(outline_generator, "STATE_DIR", state_dir)
    monkeypatch.setattr(outline_generator, "OUTLINE_PATH", state_dir / "outline.json")
    monkeypatch.setattr(outline_generator, "OUTLINE_RAW_PATH", state_dir / "outline_raw_response.txt")

    monkeypatch.setattr(retrieval, "STATE_DIR", state_dir)
    monkeypatch.setattr(retrieval, "CHUNKS_PATH", state_dir / "chunks.json")

    draft_path = state_dir / "draft_sections.json"
    monkeypatch.setattr(section_generator, "STATE_DIR", state_dir)
    monkeypatch.setattr(section_generator, "DRAFT_SECTIONS_PATH", draft_path)
    monkeypatch.setattr(revision_loop, "STATE_DIR", state_dir)
    monkeypatch.setattr(revision_loop, "DRAFT_SECTIONS_PATH", draft_path)

    monkeypatch.setattr(qc_reviewer, "STATE_DIR", state_dir)
    monkeypatch.setattr(qc_reviewer, "CHUNKS_PATH", state_dir / "chunks.json")
    monkeypatch.setattr(qc_reviewer, "QC_REPORT_PATH", state_dir / "qc_report.json")

    monkeypatch.setattr(document_assembler, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(document_assembler, "FINAL_REPORT_PATH", output_dir / "Final_Report.docx")
    monkeypatch.setattr(document_assembler, "QC_REPORT_PATH", output_dir / "QC_Report.md")

    monkeypatch.setattr(section_generator.time, "sleep", lambda *_: None)

    return {"input": DEMO_INPUT_DIR, "state": state_dir, "output": output_dir}
