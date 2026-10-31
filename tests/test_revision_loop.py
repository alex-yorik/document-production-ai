"""Offline tests for src.revision_loop (no network)."""

import src.revision_loop as revision_loop

OUTLINE = {
    "outline": [
        {
            "section_number": 1,
            "title": "Executive Summary",
            "description": "Overview",
            "key_points": ["market"],
        },
        {
            "section_number": 2,
            "title": "Market Overview",
            "description": "Market size",
            "key_points": ["data"],
        },
    ]
}


class ScriptedClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.messages = []

    def chat_completion(self, messages, *args, **kwargs):
        self.calls += 1
        self.messages.append(messages)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class SequencedQC:
    """QC callable returning preset reviews in order."""

    def __init__(self, reviews):
        self.reviews = list(reviews)
        self.calls = []

    def __call__(self, sections):
        self.calls.append(dict(sections))
        return self.reviews.pop(0)


def _issue(title="Executive Summary", description="bad claim", severity="HIGH"):
    return {
        "section": title,
        "issue_type": "factual_error",
        "severity": severity,
        "description": description,
        "suggestion": "fix it",
    }


def _review(issues, score=50):
    return {"issues": issues, "overall_score": score, "summary": "test"}


def _run_loop(tmp_path, monkeypatch, client, initial_review, qc, max_iterations=3):
    monkeypatch.setattr(revision_loop, "DRAFT_SECTIONS_PATH", tmp_path / "draft_sections.json")
    loop = revision_loop.RevisionLoop(client, [{"text": "market data"}], "methodology")
    sections = {
        "Executive Summary": "old",
        "Market Overview": "old",
    }
    return loop.run(sections, OUTLINE, initial_review, qc, max_iterations=max_iterations)


def _run(tmp_path, monkeypatch, client, issues, sections=None, max_attempts=2):
    draft_path = tmp_path / "draft_sections.json"
    monkeypatch.setattr(revision_loop, "DRAFT_SECTIONS_PATH", draft_path)
    loop = revision_loop.RevisionLoop(client, [{"text": "market data"}], "methodology")
    current = (
        sections
        if sections is not None
        else {
            "Executive Summary": "old",
            "Market Overview": "old",
        }
    )
    return loop.fix_sections(current, OUTLINE, issues, max_attempts=max_attempts)


def test_unknown_section_is_skipped(tmp_path, monkeypatch):
    client = ScriptedClient([])

    sections = _run(tmp_path, monkeypatch, client, [_issue("Unknown Section")])

    assert client.calls == 0
    assert sections == {"Executive Summary": "old", "Market Overview": "old"}


def test_issue_present_in_sections_but_not_outline_is_skipped(tmp_path, monkeypatch):
    client = ScriptedClient([])

    sections = _run(
        tmp_path,
        monkeypatch,
        client,
        [_issue("Extra Section")],
        sections={"Extra Section": "old"},
    )

    assert client.calls == 0
    assert sections == {"Extra Section": "old"}


def test_non_dict_issue_is_skipped(tmp_path, monkeypatch):
    client = ScriptedClient([])

    sections = _run(tmp_path, monkeypatch, client, ["not-a-dict"])

    assert client.calls == 0
    assert "Executive Summary" in sections


def test_duplicate_section_is_revised_once(tmp_path, monkeypatch):
    client = ScriptedClient(["revised"])

    sections = _run(
        tmp_path,
        monkeypatch,
        client,
        [_issue(), _issue(description="second issue")],
    )

    assert client.calls == 1
    assert sections["Executive Summary"] == "revised"


def test_empty_response_triggers_retry(tmp_path, monkeypatch):
    client = ScriptedClient(["   ", "revised"])

    sections = _run(tmp_path, monkeypatch, client, [_issue()])

    assert client.calls == 2
    assert sections["Executive Summary"] == "revised"


def test_exhausted_attempts_returns_false(tmp_path, monkeypatch):
    client = ScriptedClient(["", "   "])

    sections = _run(tmp_path, monkeypatch, client, [_issue()])

    assert client.calls == 2
    assert sections["Executive Summary"] == "old"


def test_client_exception_is_retried_then_exhausted(tmp_path, monkeypatch):
    client = ScriptedClient([RuntimeError("boom"), RuntimeError("boom")])

    sections = _run(tmp_path, monkeypatch, client, [_issue()])

    assert client.calls == 2
    assert sections["Executive Summary"] == "old"


def test_iterative_loop_stops_when_issues_converge(tmp_path, monkeypatch):
    client = ScriptedClient(["revised", "revised", "revised"])
    initial = _review(
        [
            _issue("Executive Summary", "bad claim one"),
            _issue("Market Overview", "bad claim two"),
        ]
    )
    qc = SequencedQC(
        [
            _review([_issue("Executive Summary", "remaining claim")], 70),
            _review([], 90),
        ]
    )

    sections, review, metrics = _run_loop(tmp_path, monkeypatch, client, initial, qc)

    assert metrics["revision_iterations"] == 2
    assert metrics["issues_per_iteration"] == [2, 1, 0]
    assert metrics["convergence_status"] == "reached"
    assert review["issues"] == []
    assert sections["Executive Summary"] == "revised"


def test_loop_stops_at_max_iterations_when_not_converged(tmp_path, monkeypatch):
    client = ScriptedClient(["revised"] * 3)
    initial = _review(
        [
            _issue("Executive Summary", "a"),
            _issue("Executive Summary", "b"),
            _issue("Executive Summary", "c"),
            _issue("Executive Summary", "d"),
        ]
    )
    qc = SequencedQC(
        [
            _review(
                [
                    _issue("Executive Summary", "a"),
                    _issue("Executive Summary", "b"),
                    _issue("Executive Summary", "c"),
                ],
                60,
            ),
            _review(
                [
                    _issue("Executive Summary", "a"),
                    _issue("Executive Summary", "b"),
                ],
                60,
            ),
            _review([_issue("Executive Summary", "a")], 60),
        ]
    )

    _sections, _review_result, metrics = _run_loop(
        tmp_path, monkeypatch, client, initial, qc, max_iterations=3
    )

    assert metrics["revision_iterations"] == 3
    assert metrics["convergence_status"] == "max_iterations"


def test_high_priority_issues_are_revised_first(tmp_path, monkeypatch):
    client = ScriptedClient(["revised", "revised"])
    initial = _review(
        [
            _issue("Market Overview", "medium issue", severity="MEDIUM"),
            _issue("Executive Summary", "high issue", severity="HIGH"),
        ]
    )
    qc = SequencedQC([_review([], 90)])

    _run_loop(tmp_path, monkeypatch, client, initial, qc)

    first_prompt = "\n".join(message["content"] for message in client.messages[0])
    assert "Section to write: Executive Summary" in first_prompt
    assert "Section to write: Market Overview" not in first_prompt


def test_revision_prompt_forbids_new_claims(tmp_path, monkeypatch):
    client = ScriptedClient(["revised"])
    initial = _review([_issue()])
    qc = SequencedQC([_review([], 90)])

    _run_loop(tmp_path, monkeypatch, client, initial, qc)

    prompt = "\n".join(message["content"] for message in client.messages[0])
    assert "не добавляй новые claims" in prompt
    assert "сохраняй факты из source documents" in prompt


def test_revision_prompt_includes_previous_history(tmp_path, monkeypatch):
    client = ScriptedClient(["revised", "revised"])
    initial = _review(
        [
            _issue("Executive Summary", "first"),
            _issue("Market Overview", "second"),
        ]
    )
    qc = SequencedQC(
        [
            _review([_issue("Executive Summary", "still broken")], 70),
            _review([], 90),
        ]
    )

    _run_loop(tmp_path, monkeypatch, client, initial, qc)

    second_iteration_prompt = "\n".join(message["content"] for message in client.messages[-1])
    assert "Previous revision history" in second_iteration_prompt


def test_low_severity_issues_are_not_revised(tmp_path, monkeypatch):
    client = ScriptedClient([])
    initial = _review([_issue(severity="LOW")])
    qc = SequencedQC([])

    _sections, review, metrics = _run_loop(tmp_path, monkeypatch, client, initial, qc)

    assert client.calls == 0
    assert metrics["revision_iterations"] == 0
    assert metrics["convergence_status"] == "reached"
    assert review == initial
