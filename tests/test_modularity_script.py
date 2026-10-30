"""Tests for scripts/check_modularity.py (CI-10)."""

from scripts.check_modularity import MAX_FILE_LINES, MAX_FUNCTION_LINES, find_violations, main


def test_compliant_project_has_no_violations(tmp_path):
    (tmp_path / "ok.py").write_text("def ok():\n    return 1\n", encoding="utf-8")

    assert find_violations(tmp_path) == []
    assert main(str(tmp_path)) == 0


def test_file_over_limit_is_reported(tmp_path):
    long_file = tmp_path / "long.py"
    long_file.write_text("# filler\n" * (MAX_FILE_LINES + 1), encoding="utf-8")

    violations = find_violations(tmp_path)

    assert len(violations) == 1
    assert "long.py" in violations[0]
    assert "file has" in violations[0]
    assert main(str(tmp_path)) == 1


def test_function_over_limit_is_reported(tmp_path):
    body = ["def too_long():"] + ["    pass"] * MAX_FUNCTION_LINES
    (tmp_path / "func.py").write_text("\n".join(body) + "\n", encoding="utf-8")

    violations = find_violations(tmp_path)

    assert len(violations) == 1
    assert "too_long" in violations[0]
    assert "function" in violations[0]


def test_excluded_directories_are_skipped(tmp_path):
    excluded = tmp_path / ".venv" / "lib"
    excluded.mkdir(parents=True)
    (excluded / "long.py").write_text("# filler\n" * (MAX_FILE_LINES + 1), encoding="utf-8")

    assert find_violations(tmp_path) == []


def test_main_reports_all_violations(tmp_path, capsys):
    (tmp_path / "long.py").write_text("# filler\n" * (MAX_FILE_LINES + 1), encoding="utf-8")

    assert main(str(tmp_path)) == 1
    assert "FAILED: 1 modularity violation(s)" in capsys.readouterr().out
