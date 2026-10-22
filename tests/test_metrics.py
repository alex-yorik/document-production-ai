"""Offline unit tests for run_pipeline metrics helpers."""

from run_pipeline import _build_metrics, count_resolved_issues


class TestCountResolvedIssues:
    def test_issue_disappeared_from_final_counts_as_resolved(self):
        draft = [{"section": "1", "description": "broken link", "severity": "HIGH"}]
        assert count_resolved_issues(draft, []) == 1

    def test_severity_downgrade_counts_as_resolved(self):
        draft = [{"section": "1", "description": "broken link", "severity": "HIGH"}]
        final = [{"section": "1", "description": "broken link", "severity": "MEDIUM"}]
        assert count_resolved_issues(draft, final) == 1

    def test_unchanged_severity_not_resolved(self):
        draft = [{"section": "1", "description": "broken link", "severity": "HIGH"}]
        final = [{"section": "1", "description": "broken link", "severity": "HIGH"}]
        assert count_resolved_issues(draft, final) == 0

    def test_empty_lists_returns_zero(self):
        assert count_resolved_issues([], []) == 0


class TestBuildMetrics:
    EXPECTED_KEYS = {
        "draft_score",
        "final_score",
        "draft_issues",
        "final_issues",
        "resolved_issues",
        "remaining_high",
        "remaining_issues",
        "resolution_rate",
    }

    def test_result_keys_exact_and_without_spaces(self):
        result = _build_metrics(
            {"issues": [], "overall_score": 50},
            {"issues": [], "overall_score": 60},
        )
        assert set(result.keys()) == self.EXPECTED_KEYS
        assert all(" " not in key for key in result.keys())

    def test_resolution_rate_zero_when_no_draft_issues(self):
        result = _build_metrics(
            {"issues": [], "overall_score": 50},
            {"issues": [], "overall_score": 60},
        )
        assert result["resolution_rate"] == 0

    def test_remaining_high_counts_only_high_severity(self):
        final_issues = [
            {"severity": "HIGH"},
            {"severity": "MEDIUM"},
            {"severity": "LOW"},
            {"severity": "HIGH"},
        ]
        result = _build_metrics(
            {"issues": [], "overall_score": 50},
            {"issues": final_issues, "overall_score": 60},
        )
        assert result["remaining_high"] == 2

    def test_scores_taken_from_overall_score(self):
        result = _build_metrics(
            {"issues": [{"severity": "HIGH"}], "overall_score": 62},
            {"issues": [], "overall_score": 72},
        )
        assert result["draft_score"] == 62
        assert result["final_score"] == 72
