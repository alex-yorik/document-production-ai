"""Quality metrics shared by the pipeline, QC report, and UI.

An issue is matched by its section and full normalized description. It counts
as resolved when it is absent from the final review or when its severity was
downgraded. There is no semantic comparison: a rephrased or downgraded issue is
treated as resolved as well.
"""

SEVERITY_ORDER = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}


def _issue_key(issue: dict) -> tuple:
    """Build the matching key: section plus normalized full description."""
    section = issue.get("section")
    description = issue.get("description") or ""
    normalized = " ".join(str(description).split()).lower()
    return (section, normalized)


def _is_resolved(draft: dict, final_by_key: dict) -> bool:
    """Return True when a draft issue disappeared or was downgraded."""
    final = final_by_key.get(_issue_key(draft))
    if final is None:
        return True
    draft_severity = SEVERITY_ORDER.get(draft.get("severity"), 0)
    final_severity = SEVERITY_ORDER.get(final.get("severity"), 0)
    return final_severity < draft_severity


def _index_final(final_issues: list) -> dict:
    """Index final issues by match key, keeping the first one per key."""
    final_by_key = {}
    for issue in final_issues:
        if isinstance(issue, dict):
            final_by_key.setdefault(_issue_key(issue), issue)
    return final_by_key


def count_resolved_issues(draft_issues: list, final_issues: list) -> int:
    """Count draft issues that disappeared or dropped in severity.

    The result is never negative: it only counts draft issues, so extra issues
    introduced in the final review cannot lower the number below zero.
    """
    final_by_key = _index_final(final_issues)
    return sum(1 for draft in draft_issues if isinstance(draft, dict) and _is_resolved(draft, final_by_key))


def count_improved_sections(draft_issues: list, final_issues: list) -> int:
    """Count distinct sections with at least one resolved draft issue."""
    final_by_key = _index_final(final_issues)
    improved = {
        draft.get("section") for draft in draft_issues if isinstance(draft, dict) and _is_resolved(draft, final_by_key)
    }
    return len(improved)
