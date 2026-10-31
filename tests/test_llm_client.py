"""Offline tests for src.llm_client (requests and sleep are faked)."""

import json
import logging

import pytest
import requests

import src.llm_client as llm_client

SECRET = "super-secret-api-key"


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


def _success(content="hello", tokens=5):
    return FakeResponse(
        {
            "choices": [{"message": {"content": content}}],
            "usage": {"completion_tokens": tokens},
        }
    )


def _make_client(monkeypatch, key=SECRET):
    monkeypatch.setattr(llm_client, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setenv("LLM_API_KEY", key)
    return llm_client.LLMClient()


def _no_sleep(monkeypatch):
    delays = []
    monkeypatch.setattr(llm_client.time, "sleep", delays.append)
    return delays


def test_init_requires_api_key(monkeypatch):
    monkeypatch.setattr(llm_client, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    with pytest.raises(ValueError, match="LLM_API_KEY is not set"):
        llm_client.LLMClient()


def test_chat_completion_success(monkeypatch):
    client = _make_client(monkeypatch)
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.update(url=url, headers=headers, payload=json, timeout=timeout)
        return _success("answer")

    monkeypatch.setattr(llm_client.requests, "post", fake_post)

    result = client.chat_completion([llm_client.format_user_message("hi")], temperature=0.1, max_tokens=10)

    assert result == "answer"
    assert captured["url"] == client.endpoint
    assert captured["headers"]["Authorization"] == f"Bearer {SECRET}"
    assert captured["payload"]["temperature"] == 0.1
    assert captured["payload"]["max_tokens"] == 10
    assert captured["timeout"] == llm_client.REQUEST_TIMEOUT_SECONDS


def test_chat_completion_retries_request_exception(monkeypatch):
    client = _make_client(monkeypatch)
    delays = _no_sleep(monkeypatch)
    attempts = []

    def fake_post(*args, **kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            raise requests.RequestException("temporary failure")
        return _success("recovered")

    monkeypatch.setattr(llm_client.requests, "post", fake_post)

    assert client.chat_completion([{"role": "user", "content": "hi"}]) == "recovered"
    assert len(attempts) == 2
    assert delays == [llm_client.RETRY_DELAY_SECONDS]


def test_chat_completion_raises_after_all_attempts(monkeypatch):
    client = _make_client(monkeypatch)
    delays = _no_sleep(monkeypatch)
    attempts = []

    def fake_post(*args, **kwargs):
        attempts.append(1)
        raise requests.RequestException("always down")

    monkeypatch.setattr(llm_client.requests, "post", fake_post)

    with pytest.raises(RuntimeError, match=f"after {llm_client.MAX_RETRIES} attempts"):
        client.chat_completion([{"role": "user", "content": "hi"}])

    assert len(attempts) == llm_client.MAX_RETRIES
    assert len(delays) == llm_client.MAX_RETRIES - 1


def test_chat_completion_key_error_on_unexpected_json(monkeypatch):
    client = _make_client(monkeypatch)
    _no_sleep(monkeypatch)
    monkeypatch.setattr(
        llm_client.requests,
        "post",
        lambda *args, **kwargs: FakeResponse({"choices": [{"message": {}}]}),
    )

    with pytest.raises(RuntimeError, match="'content'"):
        client.chat_completion([{"role": "user", "content": "hi"}])


def test_chat_completion_json_decode_error_is_retried(monkeypatch):
    client = _make_client(monkeypatch)
    delays = _no_sleep(monkeypatch)
    invalid = json.JSONDecodeError("bad json", "not json", 0)
    attempts = []

    def fake_post(*args, **kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            return FakeResponse(invalid)
        return _success('{"ok": true}')

    monkeypatch.setattr(llm_client.requests, "post", fake_post)

    assert client.chat_completion([{"role": "user", "content": "hi"}]) == '{"ok": true}'
    assert len(attempts) == 2
    assert delays == [llm_client.RETRY_DELAY_SECONDS]


def test_api_key_is_not_logged_or_leaked_in_exception(monkeypatch, caplog):
    client = _make_client(monkeypatch)
    _no_sleep(monkeypatch)
    monkeypatch.setattr(
        llm_client.requests,
        "post",
        lambda *args, **kwargs: (_ for _ in ()).throw(requests.RequestException("network down")),
    )

    with caplog.at_level(logging.DEBUG), pytest.raises(RuntimeError) as exc_info:
        client.chat_completion([{"role": "user", "content": "hi"}])

    assert SECRET not in caplog.text
    assert SECRET not in str(exc_info.value)


def test_chat_completion_json_parses_fenced_response(monkeypatch):
    client = _make_client(monkeypatch)
    received = {}

    def fake_completion(messages, **kwargs):
        received["messages"] = messages
        return '```json\n{"score": 1}\n```'

    monkeypatch.setattr(client, "chat_completion", fake_completion)

    result = client.chat_completion_json(
        [llm_client.format_user_message("review")],
        schema_description="{score: int}",
    )

    assert result == {"score": 1}
    assert received["messages"][0]["role"] == "system"
    assert "valid JSON" in received["messages"][0]["content"]


def test_chat_completion_json_without_schema_keeps_messages(monkeypatch):
    client = _make_client(monkeypatch)
    messages = [llm_client.format_user_message("review")]
    monkeypatch.setattr(client, "chat_completion", lambda *args, **kwargs: "[1, 2]")

    assert client.chat_completion_json(messages) == [1, 2]


def test_chat_completion_json_raises_value_error_on_invalid_json(monkeypatch):
    client = _make_client(monkeypatch)
    monkeypatch.setattr(client, "chat_completion", lambda *args, **kwargs: "not json")

    with pytest.raises(ValueError, match="Could not parse model output as JSON"):
        client.chat_completion_json([{"role": "user", "content": "review"}])


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  plain  ", "plain"),
        ('```json\n{"a": 1}\n```', '{"a": 1}'),
        ('```\n{"a": 1}\n```', '{"a": 1}'),
        ('```json\n{"a": 1}', '{"a": 1}'),
    ],
)
def test_strip_json_fences(raw, expected):
    assert llm_client._strip_json_fences(raw) == expected
