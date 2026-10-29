"""Consistency tests: QC report and pipeline metrics must agree on resolved."""

from src import document_assembler
from src.document_assembler import DocumentAssembler
from run_pipeline import _build_metrics


def _write_report(tmp_path, monkeypatch, draft, final):
    report_path = tmp_path / "QC_Report.md"
    monkeypatch.setattr(document_assembler, "QC_REPORT_PATH", report_path)
    DocumentAssembler().generate_quality_report(draft, final)
    return report_path.read_text(encoding="utf-8")


def test_report_and_build_metrics_agree_on_resolved(tmp_path, monkeypatch):
    draft = {
        "overall_score": 60,
        "issues": [
            {"section": "1", "description": "Missing data", "severity": "HIGH",
             "location": "p.1", "suggestion": "add"},
            {"section": "2", "description": "Vague wording", "severity": "MEDIUM",
             "location": "p.2", "suggestion": "clarify"},
            {"section": "3", "description": "Minor typo", "severity": "LOW",
             "location": "p.3", "suggestion": "fix"},
        ],
    }
    final = {
        "overall_score": 70,
        "issues": [
            {"section": "1", "description": "Missing data", "severity": "MEDIUM",
             "location": "p.1", "suggestion": "add"},
            {"section": "3", "description": "Minor typo", "severity": "LOW",
             "location": "p.3", "suggestion": "fix"},
            {"section": "4", "description": "New HIGH issue", "severity": "HIGH",
             "location": "p.4", "suggestion": "redo"},
            {"section": "5", "description": "Another new issue", "severity": "HIGH",
             "location": "p.5", "suggestion": "redo"},
        ],
    }
    metrics_resolved = _build_metrics(draft, final)["resolved_issues"]
    text = _write_report(tmp_path, monkeypatch, draft, final)
    assert f"Issues Resolved: {metrics_resolved}/{len(draft['issues'])}" in text


def test_resolved_never_negative_in_report(tmp_path, monkeypatch):
    draft = {"overall_score": 50, "issues": []}
    final = {
        "overall_score": 40,
        "issues": [
            {"section": "1", "description": "a", "severity": "HIGH"},
            {"section": "2", "description": "b", "severity": "HIGH"},
        ],
    }
    text = _write_report(tmp_path, monkeypatch, draft, final)
    assert "Issues Resolved: 0/0" in text
    assert "Issues Resolved: -" not in text


def test_negative_score_delta_not_rendered_as_plus_minus(tmp_path, monkeypatch):
    draft = {"overall_score": 70, "issues": []}
    final = {"overall_score": 65, "issues": []}
    text = _write_report(tmp_path, monkeypatch, draft, final)
    assert "+-5" not in text
    assert "-5" in text


def test_issue_without_severity_does_not_raise_in_report(tmp_path, monkeypatch):
    draft = {"overall_score": 60, "issues": [{"section": "1", "description": "no sev"}]}
    final = {"overall_score": 60, "issues": [{"section": "2", "description": "no sev"}]}
    text = _write_report(tmp_path, monkeypatch, draft, final)
    assert "Issues Resolved: 1/1" in text
