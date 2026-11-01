"""Input contract tests: required file names and fail-fast loading."""

import pytest

from run_pipeline import REQUIRED_INPUT_FILES, validate_input_dir
from src import outline_generator
from src.upload_utils import validate_uploads


class FakeUpload:
    def __init__(self, name: str) -> None:
        self.name = name

    def getvalue(self) -> bytes:
        return b"# source document\n"


def test_validate_uploads_rejects_two_files_without_company_brief():
    uploads = [FakeUpload("methodology.md"), FakeUpload("market_data.md")]

    error = validate_uploads(uploads)

    assert error is not None
    assert "company_brief.md" in error


def test_validate_uploads_accepts_three_required_files():
    uploads = [FakeUpload(name) for name in REQUIRED_INPUT_FILES]

    assert validate_uploads(uploads) is None


def test_validate_uploads_message_names_each_missing_file():
    uploads = [FakeUpload("methodology.md")]

    error = validate_uploads(uploads)

    assert error is not None
    assert "company_brief.md" in error
    assert "market_data.md" in error


def test_validate_input_dir_reports_missing_required_names(tmp_path):
    (tmp_path / "methodology.md").write_text("# Methodology", encoding="utf-8")
    with pytest.raises(ValueError) as exc_info:
        validate_input_dir(tmp_path)
    message = str(exc_info.value)
    assert "company_brief.md" in message
    assert "market_data.md" in message
    assert "demo/input" in message


def test_validate_input_dir_accepts_required_plus_extra(tmp_path):
    for name in REQUIRED_INPUT_FILES:
        (tmp_path / name).write_text(f"# {name}", encoding="utf-8")
    (tmp_path / "notes.md").write_text("# Notes", encoding="utf-8")
    validate_input_dir(tmp_path)


def test_load_input_files_raises_for_missing_required_file(tmp_path, monkeypatch):
    monkeypatch.setattr(outline_generator, "INPUT_DIR", tmp_path)
    for name in REQUIRED_INPUT_FILES:
        if name != "market_data.md":
            (tmp_path / name).write_text(name, encoding="utf-8")
    with pytest.raises(ValueError) as exc_info:
        outline_generator.load_input_files()
    assert "market_data.md" in str(exc_info.value)


def test_load_input_files_returns_only_fixed_files(tmp_path, monkeypatch):
    monkeypatch.setattr(outline_generator, "INPUT_DIR", tmp_path)
    for name in REQUIRED_INPUT_FILES:
        (tmp_path / name).write_text(f"content of {name}", encoding="utf-8")
    (tmp_path / "notes.md").write_text("extra notes", encoding="utf-8")

    brief, methodology, market_data = outline_generator.load_input_files()

    assert brief == "content of company_brief.md"
    assert methodology == "content of methodology.md"
    assert market_data == "content of market_data.md"
