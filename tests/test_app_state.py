"""UI state tests for app.py using Streamlit's AppTest harness."""

from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import run_pipeline
import src.upload_utils as upload_utils
import src.utils as utils

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"
UPLOAD_NAMES = ("company_brief.md", "methodology.md", "market_data.md")


class FakeUpload:
    def __init__(self, name: str) -> None:
        self.name = name

    def getvalue(self) -> bytes:
        return b"# source document\n"


@pytest.fixture
def uploaded_files(monkeypatch):
    """Replace the file uploader and the disk write with in-memory fakes."""
    files = [FakeUpload(name) for name in UPLOAD_NAMES]
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: files)
    monkeypatch.setattr(upload_utils, "save_uploaded_files", lambda uploaded: None)
    return files


def _metrics() -> dict:
    return {
        "draft_score": 72,
        "final_score": 85,
        "draft_issues": 10,
        "final_issues": 4,
        "resolved_issues": 6,
        "remaining_high": 0,
        "remaining_issues": [],
        "resolution_rate": 60,
    }


def _run_app(monkeypatch, output_dir: Path) -> AppTest:
    monkeypatch.setattr(utils, "OUTPUT_DIR", str(output_dir))
    at = AppTest.from_file(str(APP_PATH))
    at.run()
    return at


def test_pipeline_exception_shows_error_and_keeps_generate_button_active(monkeypatch, uploaded_files, tmp_path):
    def fail() -> dict:
        raise RuntimeError("simulated pipeline failure")

    monkeypatch.setattr(run_pipeline, "run_full_pipeline", fail)
    at = _run_app(monkeypatch, tmp_path)

    at.button(key="generate_button").click().run()

    assert not at.exception
    assert at.session_state["generation_complete"] is False
    assert "simulated pipeline failure" in at.session_state["error"]
    assert any("simulated pipeline failure" in error.value for error in at.error)
    assert at.button(key="generate_button").disabled is False

    # The error survives the next rerun, so the UI never silently loses it.
    at.run()
    assert at.session_state["generation_complete"] is False
    assert any("simulated pipeline failure" in error.value for error in at.error)
    assert at.button(key="generate_button").disabled is False


def test_successful_generation_switches_to_results(monkeypatch, uploaded_files, tmp_path):
    output = _metrics()
    monkeypatch.setattr(run_pipeline, "run_full_pipeline", lambda: output)
    at = _run_app(monkeypatch, tmp_path)

    at.button(key="generate_button").click().run()

    assert not at.exception
    assert at.session_state["generation_complete"] is True
    assert at.session_state["output"] == output
    assert at.session_state["error"] is None
    assert any("Document generated successfully!" in success.value for success in at.success)

    # Results are restored from session state after a rerun.
    at.run()
    assert at.session_state["generation_complete"] is True
    assert any("Document generated successfully!" in success.value for success in at.success)


def test_reset_button_clears_generation_state(monkeypatch, uploaded_files, tmp_path):
    output = _metrics()
    monkeypatch.setattr(run_pipeline, "run_full_pipeline", lambda: output)
    at = _run_app(monkeypatch, tmp_path)
    at.button(key="generate_button").click().run()

    at.button(key="reset_button").click().run()

    assert not at.exception
    assert at.session_state["generation_complete"] is False
    assert at.session_state["error"] is None
    assert "output" not in at.session_state
    assert not any("Document generated successfully!" in success.value for success in at.success)
