"""Tests for scripts/check_docs_consistency.py."""

from pathlib import Path

from scripts.check_docs_consistency import main

QC_REPORT = """# Quality Control Report

## Summary

### Draft Quality (before AI revision)
- Score: 76/100
- Total Issues: 12
  - HIGH: 5
  - MEDIUM: 7
  - LOW: 0

### Final Quality (after AI revision)
- Score: 84/100
- Total Issues: 12
  - HIGH: 2
  - MEDIUM: 6
  - LOW: 4

### Improvement Metrics
- Score Improvement: 76 → 84 (**+8**)
- Draft Issues No Longer Reported: 12/12 (**100%**)
- Sections Improved: 6
"""

README = """# Project

### Demo Results

| Metric | Value |
|--------|-------|
| Draft Quality Score | 76/100 |
| Final Quality Score | 84/100 |
| Score Improvement | +8 |
| Draft Issues | 12 (HIGH: 5, MEDIUM: 7, LOW: 0) |
| Final Issues | 12 (HIGH: 2, MEDIUM: 6, LOW: 4) |
| Draft Issues No Longer Reported | 12/12 (**100%**) |
| Sections Improved | 6 |
"""


def _build_repo(root: Path) -> Path:
    (root / "demo" / "expected").mkdir(parents=True)
    (root / "demo" / "expected" / "QC_Report.md").write_text(QC_REPORT, encoding="utf-8")
    (root / "README.md").write_text(README, encoding="utf-8")
    (root / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    (root / "demo" / "README.md").write_text("# Demo\n", encoding="utf-8")
    return root


def test_consistent_repository_passes(tmp_path, capsys):
    root = _build_repo(tmp_path)

    assert main(str(root)) == 0
    assert "RESULT: PASS" in capsys.readouterr().out


def test_broken_local_link_fails(tmp_path, capsys):
    root = _build_repo(tmp_path)
    readme = root / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8") + "\n[Broken](docs/missing.png)\n", encoding="utf-8")

    assert main(str(root)) == 1
    output = capsys.readouterr().out
    assert "broken link" in output
    assert "RESULT: FAIL" in output


def test_link_to_deleted_documentation_image_fails(tmp_path, capsys):
    root = _build_repo(tmp_path)
    (root / "docs").mkdir()
    (root / "docs" / "pipeline.png").write_bytes(b"png")
    readme = root / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8") + "\n![Pipeline](docs/pipeline.png)\n", encoding="utf-8")

    assert main(str(root)) == 1
    assert "deleted documentation image" in capsys.readouterr().out


def test_intermediate_model_name_fails(tmp_path, capsys):
    root = _build_repo(tmp_path)
    (root / "CHANGELOG.md").write_text("- generator: deepseek/deepseek-v4-flash\n", encoding="utf-8")

    assert main(str(root)) == 1
    assert "intermediate model" in capsys.readouterr().out


def test_metric_mismatch_fails(tmp_path, capsys):
    root = _build_repo(tmp_path)
    readme = root / "README.md"
    original = readme.read_text(encoding="utf-8")
    readme.write_text(
        original.replace("| Final Quality Score | 84/100 |", "| Final Quality Score | 80/100 |"),
        encoding="utf-8",
    )

    assert main(str(root)) == 1
    output = capsys.readouterr().out
    assert "Final Quality Score" in output
    assert "QC report has '84/100'" in output
