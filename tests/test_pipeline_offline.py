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
}


def test_pipeline_offline(offline_env, fake_client_class, monkeypatch):
    client = fake_client_class(high_issues=True)
    monkeypatch.setattr(run_pipeline, "LLMClient", lambda: client)

    metrics = run_pipeline.run_full_pipeline()

    assert set(metrics) == METRIC_KEYS
    assert (offline_env["output"] / "Final_Report.docx").is_file()
    assert (offline_env["output"] / "QC_Report.md").is_file()
    assert (offline_env["state"] / "chunks.json").is_file()


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
