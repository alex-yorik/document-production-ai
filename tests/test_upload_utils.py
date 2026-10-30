"""Offline tests for src.upload_utils (tmp_path only)."""

import pytest

from src.upload_utils import (
    MAX_UPLOAD_BYTES,
    MAX_UPLOAD_FILES,
    MIN_UPLOAD_FILES,
    clean_input_dir,
    save_uploaded_files,
    validate_uploads,
)
from src.utils import PROJECT_ROOT


class FakeUpload:
    """Minimal stand-in for streamlit UploadedFile."""

    def __init__(self, name: str, data: bytes = b"content") -> None:
        self.name = name
        self._data = data

    def getvalue(self) -> bytes:
        return self._data


def test_save_uploaded_files_sanitizes_path_traversal(tmp_path):
    save_uploaded_files([FakeUpload("../x.md", b"# hi")], input_dir=tmp_path)

    assert (tmp_path / "x.md").read_bytes() == b"# hi"
    assert not (tmp_path.parent / "x.md").exists()


@pytest.mark.parametrize("bad_name", ["notes.pdf", "script.exe", "data.md.exe", "noext"])
def test_save_uploaded_files_rejects_non_md_txt(tmp_path, bad_name):
    with pytest.raises(ValueError, match=r"Only \.md and \.txt"):
        save_uploaded_files([FakeUpload(bad_name)], input_dir=tmp_path)

    assert list(tmp_path.iterdir()) == []


def test_save_uploaded_files_does_not_clean_before_validation(tmp_path):
    (tmp_path / "keep.md").write_text("keep", encoding="utf-8")

    with pytest.raises(ValueError):
        save_uploaded_files([FakeUpload("bad.exe")], input_dir=tmp_path)

    assert (tmp_path / "keep.md").exists()


@pytest.mark.parametrize(
    "bad_dir",
    [
        PROJECT_ROOT,
        PROJECT_ROOT / "demo",
        PROJECT_ROOT / "demo" / "input",
    ],
)
def test_clean_input_dir_refuses_project_root_and_demo(bad_dir):
    with pytest.raises(ValueError, match="Refusing to clean INPUT_DIR"):
        clean_input_dir(bad_dir)


def test_clean_input_dir_deletes_only_md_and_txt(tmp_path):
    (tmp_path / "a.md").write_text("a", encoding="utf-8")
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    (tmp_path / "c.json").write_text("{}", encoding="utf-8")
    (tmp_path / "d.docx").write_bytes(b"docx")
    (tmp_path / "e.pdf").write_bytes(b"pdf")

    clean_input_dir(tmp_path)

    remaining = {path.name for path in tmp_path.iterdir()}
    assert remaining == {"c.json", "d.docx", "e.pdf"}


def test_validate_uploads_rejects_oversized_file():
    oversized = FakeUpload("methodology.md", b"x" * (MAX_UPLOAD_BYTES + 1))
    uploads = [oversized, FakeUpload("company_brief.md")]

    error = validate_uploads(uploads)

    assert error is not None
    assert "10 MB" in error


@pytest.mark.parametrize("count", [MIN_UPLOAD_FILES - 1, MAX_UPLOAD_FILES + 1])
def test_validate_uploads_rejects_count_outside_range(count):
    uploads = [FakeUpload(f"file_{index}.md") for index in range(count)]

    error = validate_uploads(uploads)

    assert error is not None
    assert f"{MIN_UPLOAD_FILES} to {MAX_UPLOAD_FILES}" in error


def test_validate_uploads_requires_methodology():
    without_methodology = [
        FakeUpload("company_brief.md"),
        FakeUpload("market_data.md"),
    ]

    error = validate_uploads(without_methodology)

    assert error is not None
    assert "methodology.md" in error


def test_validate_uploads_accepts_minimal_valid_set():
    uploads = [FakeUpload("methodology.md"), FakeUpload("company_brief.md")]

    assert validate_uploads(uploads) is None
