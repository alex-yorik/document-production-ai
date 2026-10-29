"""Offline tests for src.ingestion (tmp_path only)."""

import json

import pytest

import src.ingestion as ingestion


def test_chunk_text_returns_single_chunk_at_boundary():
    text = "a" * 500

    assert ingestion.chunk_text(text, chunk_size=500, overlap=50) == [text]


def test_chunk_text_splits_with_overlap():
    text = "abcdefghij"

    chunks = ingestion.chunk_text(text, chunk_size=4, overlap=1)

    assert chunks == ["abcd", "defg", "ghij"]
    assert chunks[0][-1] == chunks[1][0]
    assert chunks[1][-1] == chunks[2][0]


def test_chunk_text_uses_zero_overlap():
    assert ingestion.chunk_text("abcdefgh", chunk_size=4, overlap=0) == [
        "abcd",
        "efgh",
    ]


def test_chunk_text_normalizes_crlf():
    chunks = ingestion.chunk_text("a\r\nb\r\nc", chunk_size=100, overlap=0)

    assert chunks == ["a\nb\nc"]
    assert "\r" not in chunks[0]


@pytest.mark.parametrize(
    ("chunk_size", "overlap", "match"),
    [
        (0, 0, "chunk_size must be a positive integer"),
        (-1, 0, "chunk_size must be a positive integer"),
        (10, -1, r"overlap must be in range"),
        (10, 10, r"overlap must be in range"),
        (10, 11, r"overlap must be in range"),
    ],
)
def test_chunk_text_rejects_invalid_parameters(chunk_size, overlap, match):
    with pytest.raises(ValueError, match=match):
        ingestion.chunk_text("some text", chunk_size=chunk_size, overlap=overlap)


def test_read_file_reads_supported_extension(tmp_path):
    path = tmp_path / "notes.MD"
    path.write_text("# Title", encoding="utf-8")

    assert ingestion.read_file(path) == "# Title"


def test_read_file_rejects_unsupported_extension(tmp_path):
    path = tmp_path / "notes.pdf"
    path.write_text("pdf", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file extension"):
        ingestion.read_file(path)


def test_process_documents_chunks_and_persists(tmp_path, monkeypatch):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "a.md").write_text("abcdefghij", encoding="utf-8")
    (input_dir / "b.txt").write_text("hello", encoding="utf-8")
    (input_dir / "ignored.pdf").write_text("pdf", encoding="utf-8")
    output = tmp_path / "chunks.json"

    monkeypatch.setattr(ingestion, "INPUT_DIR", input_dir)
    monkeypatch.setattr(ingestion, "CHUNKS_OUTPUT", output)

    chunks = ingestion.process_documents(chunk_size=5, overlap=0)

    assert chunks == [
        {"source_file": "a.md", "chunk_index": 0, "text": "abcde"},
        {"source_file": "a.md", "chunk_index": 1, "text": "fghij"},
        {"source_file": "b.txt", "chunk_index": 0, "text": "hello"},
    ]
    assert json.loads(output.read_text(encoding="utf-8")) == chunks


def test_process_documents_missing_input_dir_returns_empty(tmp_path, monkeypatch):
    output = tmp_path / "chunks.json"

    monkeypatch.setattr(ingestion, "INPUT_DIR", tmp_path / "missing")
    monkeypatch.setattr(ingestion, "CHUNKS_OUTPUT", output)

    assert ingestion.process_documents() == []
    assert json.loads(output.read_text(encoding="utf-8")) == []
