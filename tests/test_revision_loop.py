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

    def chat_completion(self, *args, **kwargs):
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _issue(title="Executive Summary", description="bad claim"):
    return {
        "section": title,
        "issue_type": "factual_error",
        "severity": "HIGH",
        "description": description,
        "suggestion": "fix it",
    }


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
