"""Unit tests for the QCReviewer numeric traceability check."""

from src.qc_reviewer import QCReviewer


def _chunk(text: str) -> dict:
    return {"text": text}


def _reviewer(chunks: list) -> QCReviewer:
    return QCReviewer(client=None, all_chunks=chunks)


class TestNumericTraceability:
    def test_number_present_in_source_is_not_reported(self):
        reviewer = _reviewer([_chunk("Revenue grew 42% in 2025.")])

        review = reviewer._check_numeric_traceability({"Summary": "Revenue grew 42%."})

        assert review["issues"] == []

    def test_missing_number_reports_one_automated_issue(self):
        reviewer = _reviewer([_chunk("Revenue grew 42% in 2025.")])

        review = reviewer._check_numeric_traceability({"Summary": "Growth reached 99%."})

        assert len(review["issues"]) == 1
        issue = review["issues"][0]
        assert issue["issue_type"] == "numeric_traceability_check"
        assert "(automated check)" in issue["description"]
        assert issue["severity"] == "HIGH"

    def test_space_before_percent_in_source_is_normalized(self):
        reviewer = _reviewer([_chunk("Revenue grew 80 % year over year.")])

        review = reviewer._check_numeric_traceability({"Summary": "Revenue grew 80%."})

        assert review["issues"] == []

    def test_number_split_across_chunk_boundary_is_found(self):
        reviewer = _reviewer([_chunk("Revenue reached 7."), _chunk("5% growth.")])

        review = reviewer._check_numeric_traceability(
            {"Summary": "Revenue reached 7.5%."}
        )

        assert review["issues"] == []

    def test_empty_sections_and_empty_text_do_not_fail(self):
        reviewer = _reviewer([_chunk("Revenue grew 42%.")])

        assert reviewer._check_numeric_traceability({})["issues"] == []
        assert reviewer._check_numeric_traceability({"Empty": ""})["issues"] == []

    def test_missing_chunks_are_loaded_lazily(self, monkeypatch):
        reviewer = QCReviewer(client=None, all_chunks=None)
        calls = []

        def fake_ensure_chunks():
            calls.append(True)
            reviewer.all_chunks = [_chunk("Revenue grew 42%.")]

        monkeypatch.setattr(reviewer, "_ensure_chunks", fake_ensure_chunks)

        review = reviewer._check_numeric_traceability({"Summary": "Revenue grew 42%."})

        assert calls == [True]
        assert review["issues"] == []

    def test_all_numbers_are_checked_without_arbitrary_cap(self):
        source = " ".join(f"value {number}%" for number in range(10))
        reviewer = _reviewer([_chunk(source)])
        section_text = " ".join(f"value {number}%" for number in range(10, 16))

        review = reviewer._check_numeric_traceability({"Summary": section_text})

        assert len(review["issues"]) == 6
