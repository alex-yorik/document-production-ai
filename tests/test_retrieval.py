"""Offline tests for src.retrieval (no filesystem or network)."""

import pytest

import src.retrieval as retrieval

CHUNKS = [
    {"source_file": "a.md", "chunk_index": 0, "text": "market size and growth"},
    {"source_file": "a.md", "chunk_index": 1, "text": "entry strategy options"},
    {"source_file": "b.md", "chunk_index": 0, "text": "market entry risks"},
    {"source_file": "b.md", "chunk_index": 1, "text": "unrelated content"},
]


def test_keyword_search_ranks_by_match_count():
    results = retrieval.keyword_search("market entry strategy", CHUNKS, top_k=3)

    texts = [chunk["text"] for chunk in results]
    assert texts[:2] == ["entry strategy options", "market entry risks"]


def test_keyword_search_respects_top_k():
    results = retrieval.keyword_search("market", CHUNKS, top_k=1)

    assert len(results) == 1
    assert results[0]["text"] == "market size and growth"


def test_keyword_search_returns_first_chunks_when_all_scores_zero():
    results = retrieval.keyword_search("zzz", CHUNKS, top_k=2)

    assert results == CHUNKS[:2]


def test_get_relevant_chunks_for_section_strips_special_characters():
    chunks = [
        {"text": "market overview data"},
        {"text": "other content"},
    ]

    results = retrieval.get_relevant_chunks_for_section("Market: Overview! (2024)", chunks, top_k=1)

    assert results == ["market overview data"]


def test_get_relevant_chunks_for_section_only_special_characters():
    results = retrieval.get_relevant_chunks_for_section("!!!", CHUNKS, top_k=2)

    assert results == [chunk["text"] for chunk in CHUNKS[:2]]


def test_format_context_joins_chunks():
    assert retrieval.format_context(["one", "two"]) == ("Relevant context:\none\n\n---\n\ntwo")


def test_format_context_empty_list():
    assert retrieval.format_context([]) == "Relevant context:\n"


def test_load_chunks_rejects_non_list(monkeypatch):
    monkeypatch.setattr(retrieval, "load_json", lambda _path: {"not": "a list"})

    with pytest.raises(ValueError, match="Expected a JSON list"):
        retrieval.load_chunks()
