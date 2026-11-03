"""Documentation consistency gate.

Checks that the published documentation cannot drift from the actual demo
results and repository contents:

(a) the Demo Results table in README.md matches demo/expected/QC_Report.md;
(b) every local link and image in every repository ``*.md`` file exists;
(c) no link or image points at the removed documentation screenshots;
(d) README.md, CHANGELOG.md and demo/README.md do not mention intermediate
    model names that were only used during development.

The script prints a human-readable summary and exits 0 on success or 1 on any
failure. It uses only the standard library.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

README = "README.md"
QC_REPORT = "demo/expected/QC_Report.md"
MODEL_FILES = ("README.md", "CHANGELOG.md", "demo/README.md")
DELETED_IMAGES = (
    "docs/pipeline.png",
    "docs/qc-report.png",
    "docs/final-document.png",
)
MODEL_PATTERN = re.compile(r"gpt-4o-mini|deepseek-v4-flash|deepseek/deepseek", re.IGNORECASE)

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "node_modules",
    "graphify-out",
    "output",
    "project_state",
    ".claude",
    ".opencode",
}

METRIC_LABELS = {
    "Draft Quality Score": "draft_quality_score",
    "Final Quality Score": "final_quality_score",
    "Score Improvement": "score_improvement",
    "Draft Issues": "draft_issues",
    "Final Issues": "final_issues",
    "Draft Issues No Longer Reported": "resolved_issues",
    "Sections Improved": "sections_improved",
}

LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HTML_ATTR_RE = re.compile(r"""(?:src|href)\s*=\s*["']([^"']+)["']""")
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
FENCE_RE = re.compile(r"```.*?```", re.S)
INLINE_CODE_RE = re.compile(r"`[^`]*`")


def _normalize(value: str) -> str:
    """Collapse markdown emphasis and whitespace for a fair text comparison."""
    return " ".join(value.replace("*", "").replace("`", "").split())


def _capture(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1).strip() if match else None


def _capture_int(pattern: str, text: str) -> int | None:
    value = _capture(pattern, text)
    return int(value) if value is not None and value.isdigit() else None


def parse_qc_report(text: str) -> dict[str, str] | None:
    """Extract the seven metrics from demo/expected/QC_Report.md."""
    draft_start = text.find("Draft Quality")
    final_start = text.find("Final Quality")
    improvement_start = text.find("Improvement Metrics")
    if -1 in (draft_start, final_start, improvement_start):
        return None

    draft_block = text[draft_start:final_start]
    final_block = text[final_start:improvement_start]
    improvement_block = text[improvement_start:]

    draft_counts = {
        "total": _capture_int(r"Total Issues:\s*(\d+)", draft_block),
        "high": _capture_int(r"HIGH:\s*(\d+)", draft_block),
        "medium": _capture_int(r"MEDIUM:\s*(\d+)", draft_block),
        "low": _capture_int(r"LOW:\s*(\d+)", draft_block),
    }
    final_counts = {
        "total": _capture_int(r"Total Issues:\s*(\d+)", final_block),
        "high": _capture_int(r"HIGH:\s*(\d+)", final_block),
        "medium": _capture_int(r"MEDIUM:\s*(\d+)", final_block),
        "low": _capture_int(r"LOW:\s*(\d+)", final_block),
    }
    draft_score = _capture(r"Score:\s*(\d+/100)", draft_block)
    final_score = _capture(r"Score:\s*(\d+/100)", final_block)
    score_improvement = _capture(r"Score Improvement:.*?\(([^)]+)\)", improvement_block)
    resolved = _capture(r"Draft Issues No Longer Reported:\s*([^\n]+)", improvement_block)
    sections_improved = _capture(r"Sections Improved:\s*(\d+)", improvement_block)

    values = {
        "draft_quality_score": draft_score,
        "final_quality_score": final_score,
        "score_improvement": score_improvement,
        "draft_issues": _format_issue_counts(draft_counts),
        "final_issues": _format_issue_counts(final_counts),
        "resolved_issues": resolved,
        "sections_improved": sections_improved,
    }
    if any(value is None for value in values.values()):
        return None
    return {key: _normalize(value) for key, value in values.items()}


def _format_issue_counts(counts: dict[str, int | None]) -> str | None:
    if any(value is None for value in counts.values()):
        return None
    return f"{counts['total']} (HIGH: {counts['high']}, MEDIUM: {counts['medium']}, LOW: {counts['low']})"


def parse_readme_metrics(text: str) -> dict[str, str] | None:
    """Extract the Demo Results table from README.md."""
    heading = re.search(r"^###\s+Demo Results\s*$", text, re.MULTILINE | re.IGNORECASE)
    if heading is None:
        return None

    metrics: dict[str, str] = {}
    in_table = False
    for line in text[heading.end() :].splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            in_table = True
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if len(cells) < 2 or all(set(cell) <= set("-: ") for cell in cells):
                continue
            if cells[0].strip().lower() == "metric":
                continue
            metrics[cells[0]] = cells[1]
        elif in_table and stripped:
            break
    if not metrics:
        return None
    return metrics


def check_metrics(root: Path) -> list[str]:
    """Check (a): README Demo Results equals the QC report metrics."""
    readme_path = root / README
    qc_path = root / QC_REPORT
    if not readme_path.is_file() or not qc_path.is_file():
        return [f"missing {README} or {QC_REPORT}"]

    expected = parse_qc_report(qc_path.read_text(encoding="utf-8"))
    actual = parse_readme_metrics(readme_path.read_text(encoding="utf-8"))
    if expected is None:
        return [f"{QC_REPORT}: could not parse the seven metrics"]
    if actual is None:
        return [f"{README}: could not parse the Demo Results table"]

    errors: list[str] = []
    missing = sorted(set(METRIC_LABELS) - set(actual))
    extra = sorted(set(actual) - set(METRIC_LABELS))
    if missing:
        errors.append(f"{README}: missing metric rows: {', '.join(missing)}")
    if extra:
        errors.append(f"{README}: unexpected metric rows: {', '.join(extra)}")

    for label, key in METRIC_LABELS.items():
        if label not in actual:
            continue
        readme_value = _normalize(actual[label])
        qc_value = expected[key]
        if readme_value != qc_value:
            errors.append(f"{README}: '{label}' is '{readme_value}', QC report has '{qc_value}'")
    return errors


def _iter_markdown_files(root: Path):
    for path in sorted(root.rglob("*.md")):
        if any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts):
            continue
        yield path


def _iter_links(root: Path):
    """Yield (markdown file, original target, cleaned target) for local targets."""
    for path in _iter_markdown_files(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        text = FENCE_RE.sub("", text)
        text = INLINE_CODE_RE.sub("", text)
        targets = [match.group(1) for match in LINK_RE.finditer(text)]
        targets.extend(match.group(1) for match in HTML_ATTR_RE.finditer(text))
        for raw in targets:
            target = raw.strip()
            if target.startswith("<") and ">" in target:
                target = target[1 : target.find(">")]
            else:
                target = target.split()[0] if target.split() else ""
            target = target.strip("\"'")
            if not target or target.startswith("#") or target.startswith("//"):
                continue
            if SCHEME_RE.match(target):
                continue
            cleaned = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if cleaned:
                yield path, target, cleaned


def check_links(root: Path) -> tuple[int, list[str]]:
    """Check (b): every local link and image resolves on disk."""
    errors: list[str] = []
    checked = 0
    for path, target, cleaned in _iter_links(root):
        checked += 1
        if cleaned.startswith("/"):
            resolved = (root / cleaned.lstrip("/")).resolve()
        else:
            resolved = (path.parent / cleaned).resolve()
        if not resolved.exists():
            errors.append(f"{path.relative_to(root)}: broken link '{target}'")
    return checked, errors


def check_deleted_images(root: Path) -> list[str]:
    """Check (c): no link or image points at a removed screenshot."""
    errors: list[str] = []
    for path, target, cleaned in _iter_links(root):
        normalized = cleaned[2:] if cleaned.startswith("./") else cleaned
        for deleted in DELETED_IMAGES:
            if normalized == deleted or normalized.endswith("/" + deleted):
                errors.append(f"{path.relative_to(root)}: references deleted documentation image '{target}'")
    return errors


def check_model_names(root: Path) -> list[str]:
    """Check (d): no intermediate model names in user-facing documentation."""
    errors: list[str] = []
    for relative in MODEL_FILES:
        path = root / relative
        if not path.is_file():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if MODEL_PATTERN.search(line):
                errors.append(f"{relative}:{number}: mentions an intermediate model: {line.strip()}")
    return errors


def _report(title: str, errors: list[str]) -> bool:
    if errors:
        print(f"FAIL: {title}")
        for error in errors:
            print(f"  - {error}")
        return False
    print(f"OK: {title}")
    return True


def main(root: str = ".") -> int:
    """Run all documentation checks; return 0 when everything is consistent."""
    root_path = Path(root).resolve()
    print(f"Documentation consistency check: {root_path}")

    passed = _report(
        "README Demo Results matches demo/expected/QC_Report.md (7 metrics)",
        check_metrics(root_path),
    )

    checked, link_errors = check_links(root_path)
    passed = _report(f"all {checked} local links and images exist", link_errors) and passed

    passed = (
        _report(
            "no links to removed documentation images",
            check_deleted_images(root_path),
        )
        and passed
    )

    passed = (
        _report(
            "no intermediate model names in README/CHANGELOG/demo README",
            check_model_names(root_path),
        )
        and passed
    )

    print("RESULT: PASS" if passed else "RESULT: FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
