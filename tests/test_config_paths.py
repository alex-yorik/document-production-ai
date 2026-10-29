"""Tests for cwd-independent state paths and client configuration."""

import json

import pytest

import run_pipeline
import src.llm_client as llm_client
import src.qc_reviewer as qc_reviewer
import src.retrieval as retrieval
import src.revision_loop as revision_loop
import src.section_generator as section_generator
from src.llm_client import DeepSeekClient, _strip_json_fences
from src.qc_reviewer import QCReviewer
from src.revision_loop import RevisionLoop
from src.utils import PROJECT_ROOT, STATE_DIR


def test_state_dir_is_absolute():
    assert STATE_DIR.is_absolute()
    assert STATE_DIR == PROJECT_ROOT / "project_state"


def test_module_paths_are_built_from_state_dir():
    assert retrieval.CHUNKS_PATH == STATE_DIR / "chunks.json"
    assert qc_reviewer.CHUNKS_PATH == STATE_DIR / "chunks.json"
    assert qc_reviewer.QC_REPORT_PATH == STATE_DIR / "qc_report.json"
    assert revision_loop.DRAFT_SECTIONS_PATH == STATE_DIR / "draft_sections.json"
    assert section_generator.DRAFT_SECTIONS_PATH == STATE_DIR / "draft_sections.json"
    assert run_pipeline.CHUNKS_PATH == STATE_DIR / "chunks.json"


def test_retrieval_load_chunks_works_after_chdir(monkeypatch, tmp_path):
    chunks_file = tmp_path / "chunks.json"
    chunks_file.write_text(json.dumps([{"text": "hello"}]), encoding="utf-8")
    monkeypatch.setattr(retrieval, "CHUNKS_PATH", chunks_file)
    monkeypatch.chdir(tmp_path)

    assert retrieval.load_chunks() == [{"text": "hello"}]


class _FakeJsonClient:
    def chat_completion_json(self, *args, **kwargs):
        return {"issues": [], "overall_score": 88, "summary": "ok"}


def test_qc_reviewer_writes_report_after_chdir(monkeypatch, tmp_path):
    report_path = tmp_path / "qc_report.json"
    monkeypatch.setattr(qc_reviewer, "QC_REPORT_PATH", report_path)
    monkeypatch.chdir(tmp_path)
    reviewer = QCReviewer(client=_FakeJsonClient(), all_chunks=[{"text": "Revenue grew 42%."}])

    review = reviewer.review_sections({"Summary": "Revenue grew 42%."}, {"outline": []}, "")

    assert review["overall_score"] == 88
    saved = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved["overall_score"] == 88


class _FakeTextClient:
    def chat_completion(self, *args, **kwargs):
        return "Revised section text."


class _FakeGenerator:
    def _build_messages(self, *args, **kwargs):
        return []


def test_revision_loop_writes_draft_after_chdir(monkeypatch, tmp_path):
    draft_path = tmp_path / "draft_sections.json"
    monkeypatch.setattr(revision_loop, "DRAFT_SECTIONS_PATH", draft_path)
    monkeypatch.chdir(tmp_path)
    loop = RevisionLoop(client=_FakeTextClient(), all_chunks=[], methodology_text="")
    sections = {"Summary": "old"}

    fixed = loop._revise_section(
        _FakeGenerator(),
        sections,
        {"title": "Summary"},
        {"section": "Summary", "description": "bad", "suggestion": "fix"},
        1,
    )

    assert fixed is True
    assert sections["Summary"] == "Revised section text."
    assert json.loads(draft_path.read_text(encoding="utf-8")) == sections


def _make_client(
    monkeypatch,
    base_url: str = "https://example.test/v1",
    model: str = "custom-model",
) -> DeepSeekClient:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", base_url)
    monkeypatch.setenv("MODEL_NAME", model)
    return DeepSeekClient()


def test_client_reads_env_after_module_import(monkeypatch):
    client = _make_client(monkeypatch, "https://late.example/v1", "late-model")

    assert client.base_url == "https://late.example/v1"
    assert client.model == "late-model"
    assert client.endpoint == "https://late.example/v1/chat/completions"


def test_retry_and_timeout_constants_are_named():
    assert llm_client.MAX_RETRIES == 3
    assert llm_client.REQUEST_TIMEOUT_SECONDS == 60


def test_chat_completion_json_parses_once_and_raises_value_error(monkeypatch):
    client = _make_client(monkeypatch)
    monkeypatch.setattr(client, "chat_completion", lambda *a, **kw: "not valid json")
    calls = []
    real_loads = json.loads

    def counting_loads(value):
        calls.append(value)
        return real_loads(value)

    monkeypatch.setattr(llm_client.json, "loads", counting_loads)

    with pytest.raises(ValueError, match="Could not parse model output as JSON"):
        client.chat_completion_json([{"role": "user", "content": "hi"}])

    assert len(calls) == 1


@pytest.mark.parametrize(
    "raw, expected",
    [
        ('```json\n{"a": 1}\n```', '{"a": 1}'),
        ('```\n{"a": 1}\n```', '{"a": 1}'),
        ("  ```json\n[1, 2]\n```  ", "[1, 2]"),
    ],
)
def test_strip_json_fences(raw, expected):
    assert _strip_json_fences(raw) == expected


def test_model_none_uses_instance_model(monkeypatch):
    client = _make_client(monkeypatch, model="instance-model")
    captured = {}

    def fake_completion(messages, model=None, temperature=0.0, max_tokens=2000):
        captured["model"] = model
        return '{"ok": true}'

    monkeypatch.setattr(client, "chat_completion", fake_completion)

    result = client.chat_completion_json([{"role": "user", "content": "hi"}], model=None)

    assert result == {"ok": True}
    assert captured["model"] == "instance-model"
