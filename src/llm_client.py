"""DeepSeek LLM client for chat completions and structured JSON output."""

import json
import logging
import os
import time

import requests
from dotenv import load_dotenv

BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEFAULT_MODEL = os.getenv("MODEL_NAME", "deepseek-chat")

CHAT_ENDPOINT = f"{BASE_URL}/chat/completions"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2.0

logger = logging.getLogger(__name__)


def format_user_message(text: str) -> dict[str, str]:
    """Build a user message dict for the chat API."""
    return {"role": "user", "content": text}


def format_system_message(text: str) -> dict[str, str]:
    """Build a system message dict for the chat API."""
    return {"role": "system", "content": text}


def _strip_json_fences(raw: str) -> str:
    """Remove markdown code fences and surrounding whitespace from a raw response."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```")
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].rstrip()
    return cleaned.strip()


class DeepSeekClient:
    """Minimal OpenAI-compatible client for the DeepSeek chat API."""

    def __init__(self) -> None:
        """Load API credentials from environment variables."""
        load_dotenv()
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", BASE_URL)
        if not self.api_key:
            raise ValueError(
                "DEEPSEEK_API_KEY is not set. "
                "Create a .env file in the project root (see .env.example) or export the variable."
            )
        self.endpoint = f"{self.base_url}/chat/completions"

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str = DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """Send a chat completion request with retries and timing logs.

        Args:
            messages: List of {"role": ..., "content": ...} messages.
            model: Model identifier to use.
            temperature: Sampling temperature (0.0-2.0).
            max_tokens: Maximum number of tokens to generate.

        Returns:
            The assistant text response.

        Raises:
            RuntimeError: If all retries are exhausted or the API returns an error.
        """
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            started_at = time.monotonic()
            try:
                response = requests.post(self.endpoint, headers=headers, json=payload, timeout=60)
                elapsed = time.monotonic() - started_at
                logger.debug(
                    "chat_completion attempt %d/%d took %.2fs (status %d)",
                    attempt,
                    MAX_RETRIES,
                    elapsed,
                    response.status_code,
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                logger.info("chat_completion ok in %.2fs (%d tokens)", elapsed, data.get("usage", {}).get("completion_tokens", 0))
                return content
            except (requests.RequestException, KeyError, json.JSONDecodeError) as exc:
                last_error = exc
                logger.warning(
                    "chat_completion attempt %d/%d failed: %s",
                    attempt,
                    MAX_RETRIES,
                    exc,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY_SECONDS)
        raise RuntimeError(f"chat_completion failed after {MAX_RETRIES} attempts: {last_error}")

    def chat_completion_json(
        self,
        messages: list[dict[str, str]],
        schema_description: str | None = None,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.0,
        max_tokens: int = 2000,
    ) -> dict | list:
        """Request a JSON-only response and parse it robustly.

        Args:
            messages: Base conversation messages.
            schema_description: Human-readable JSON schema to request.
                Prepended as a system message when provided.
            model: Model identifier to use.
            temperature: Sampling temperature (0.0-2.0).
            max_tokens: Maximum number of tokens to generate.

        Returns:
            Parsed JSON object (dict or list).

        Raises:
            ValueError: If the response cannot be parsed as JSON.
        """
        if schema_description:
            system_prompt = (
                f"Return ONLY valid JSON matching this schema: {schema_description}. "
                "Do not include markdown, prose or explanations."
            )
            full_messages = [
                format_system_message(system_prompt),
                *messages,
            ]
        else:
            full_messages = list(messages)
        raw = self.chat_completion(
            full_messages, model=model, temperature=temperature, max_tokens=max_tokens
        )
        try:
            return json.loads(_strip_json_fences(raw))
        except json.JSONDecodeError:
            logger.warning("Raw response was not valid JSON; retrying once after cleaning")
        cleaned = _strip_json_fences(raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Could not parse model output as JSON: {raw[:500]}") from exc
