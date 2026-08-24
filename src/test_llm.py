"""Manual test/demo for the DeepSeek client and keyword retrieval."""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.llm_client import DeepSeekClient
from src.retrieval import keyword_search, load_chunks
from src.utils import load_env


def setup_logging() -> None:
    """Configure console logging with timestamps."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


def test_llm() -> None:
    """Run a basic chat completion and print the result."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"},
    ]
    client = DeepSeekClient()
    response = client.chat_completion(messages, temperature=0.3)
    print("\nLLM response:", response)
    print("✅ LLM client works!")


def test_retrieval() -> None:
    """Run a keyword search over ingested chunks and print results."""
    chunks = load_chunks()
    query = "market size statistics"
    results = keyword_search(query, chunks, top_k=2)
    print(f"\nRetrieval results for query '{query}':")
    for idx, chunk in enumerate(results, start=1):
        snippet = chunk["text"].replace("\n", " ")[:160]
        print(f"  [{idx}] {chunk['source_file']} (chunk {chunk['chunk_index']}): {snippet}...")
    print("✅ Retrieval works!")


def main() -> int:
    """Run both manual tests."""
    setup_logging()
    load_env()
    test_llm()
    test_retrieval()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
