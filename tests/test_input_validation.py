"""Offline tests for run_pipeline.validate_input_dir (tmp_path only)."""

import pytest

from run_pipeline import validate_input_dir


def test_missing_dir_raises_with_name_and_demo_hint(tmp_path):
    missing = tmp_path / "nonexistent_dir"
    with pytest.raises(ValueError) as exc_info:
        validate_input_dir(missing)
    message = str(exc_info.value)
    assert "nonexistent_dir" in message
    assert "demo" in message


def test_missing_methodology_md_raises(tmp_path):
    (tmp_path / "brief.md").write_text("# Brief", encoding="utf-8")
    with pytest.raises(ValueError) as exc_info:
        validate_input_dir(tmp_path)
    assert "methodology.md" in str(exc_info.value)


def test_missing_required_sources_raises(tmp_path):
    (tmp_path / "methodology.md").write_text("# Methodology", encoding="utf-8")
    with pytest.raises(ValueError) as exc_info:
        validate_input_dir(tmp_path)
    message = str(exc_info.value)
    assert "company_brief.md" in message
    assert "market_data.md" in message


def test_valid_dir_with_all_required_files_does_not_raise(tmp_path):
    (tmp_path / "company_brief.md").write_text("# Brief", encoding="utf-8")
    (tmp_path / "market_data.md").write_text("# Market data", encoding="utf-8")
    (tmp_path / "methodology.md").write_text("# Methodology", encoding="utf-8")
    validate_input_dir(tmp_path)
