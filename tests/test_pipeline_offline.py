"""Offline end-to-end tests for run_pipeline with a deterministic FakeClient."""

import logging

import pytest

import run_pipeline

METRIC_KEYS = {
    "draft_score",
    "final_score",
    "draft_issues",
    "final_issues",
    "resolved_issues",
    "remaining_high",
    "remaining_issues",
    "resolution_rate",
    "revision_iterations",
    "issues_per_iteration",
    "convergence_status",
    "improvement_score",
}


def _issue(description: str) -> dict:
    return {
        "section": "Executive Summary",
        "issue_type": "factual_error",
        "severity": "HIGH",
        "description": description,
        "location": "Executive Summary paragraph 2",
        "suggestion": "Remove the claim or add source support.",
    }


def test_pipeline_offline(offline_env, fake_client_class, monkeypatch):
    client = fake_client_class(high_issues=True)
    monkeypatch.setattr(run_pipeline, "LLMClient", lambda: client)

    metrics = run_pipeline.run_full_pipeline()

    assert set(metrics) == METRIC_KEYS
    assert (offline_env["output"] / "Final_Report.docx").is_file()
    assert (offline_env["output"] / "QC_Report.md").is_file()
    assert (offline_env["state"] / "chunks.json").is_file()
    assert metrics["revision_iterations"] >= 1
    assert metrics["convergence_status"] == "reached"
    assert metrics["improvement_score"] > 0


def test_pipeline_continues_while_issues_improve(offline_env, fake_client_class, monkeypatch):
    class ConvergingClient(fake_client_class):
        def _qc_report(self, *, is_draft):
            if self.qc_calls == 1:
                return {
                    "issues": [_issue("first"), _issue("second")],
                    "overall_score": 50,
                    "summary": "Draft review with two HIGH issues.",
                }
            if self.qc_calls == 2:
                return {
                    "issues": [_issue("first")],
                    "overall_score": 75,
                    "summary": "Intermediate review with one HIGH issue.",
                }
            return {
                "issues": [],
                "overall_score": 92,
                "summary": "Final review with no issues.",
            }

    client = ConvergingClient(high_issues=True)
    monkeypatch.setattr(run_pipeline, "LLMClient", lambda: client)

    metrics = run_pipeline.run_full_pipeline()

    assert metrics["revision_iterations"] == 2
    assert metrics["issues_per_iteration"] == [2, 1, 0]
    assert metrics["convergence_status"] == "reached"
    assert metrics["improvement_score"] == 2
    assert client.revision_calls >= 2


@pytest.mark.parametrize(
    ("high_issues", "revision_expected"),
    [(True, True), (False, False)],
)
def test_revision_depends_on_high_issues(offline_env, fake_client_class, monkeypatch, high_issues, revision_expected):
    client = fake_client_class(high_issues=high_issues)
    monkeypatch.setattr(run_pipeline, "LLMClient", lambda: client)

    metrics = run_pipeline.run_full_pipeline()

    assert (client.revision_calls > 0) is revision_expected
    if revision_expected:
        assert metrics["draft_issues"] >= 1


def test_qc_exception_is_contained_with_zero_score(offline_env, fake_client_class, monkeypatch, caplog):
    client = fake_client_class(qc_raises=True)
    monkeypatch.setattr(run_pipeline, "LLMClient", lambda: client)

    with caplog.at_level(logging.WARNING):
        metrics = run_pipeline.run_full_pipeline()

    assert metrics["final_score"] == 0
    assert client.revision_calls == 0
    assert any(record.levelno >= logging.WARNING and "QC review" in record.getMessage() for record in caplog.records)
