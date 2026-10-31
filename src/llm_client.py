"""OpenRouter LLM client with separate generator and QC model configurations."""

import json
import logging
import os
import time
from typing import NamedTuple

import requests
from dotenv import load_dotenv

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_GENERATOR_MODEL = "openai/gpt-4o-mini"
DEFAULT_QC_MODEL = "z-ai/glm-5.3-flash"
DEFAULT_MODEL_NAME = DEFAULT_GENERATOR_MODEL
CONFIG_GENERATOR = "generator"
CONFIG_QC = "qc"
CHAT_ENDPOINT_PATH = "/chat/completions"

# Maximum number of attempts before chat_completion gives up.
MAX_RETRIES = 3
# Delay between failed attempts, in seconds.
RETRY_DELAY_SECONDS = 2.0
# HTTP request timeout for a single chat completion call, in seconds.
REQUEST_TIMEOUT_SECONDS = 60

logger = logging.getLogger(__name__)


class LLMConfig(NamedTuple):
    """Resolved settings for one LLM role."""

    api_key: str | None
    base_url: str
    model: str


def _load_config(config: str) -> LLMConfig:
    """Resolve API key, base URL and model for a named LLM role."""
    if config == CONFIG_GENERATOR:
        api_key = os.getenv("GENERATOR_API_KEY") or os.getenv("LLM_API_KEY")
        base_url = os.getenv("GENERATOR_BASE_URL") or os.getenv("LLM_BASE_URL") or DEFAULT_BASE_URL
        model = os.getenv("GENERATOR_MODEL") or os.getenv("LLM_MODEL") or DEFAULT_GENERATOR_MODEL
    elif config == CONFIG_QC:
        api_key = os.getenv("QC_API_KEY") or os.getenv("LLM_API_KEY")
        base_url = os.getenv("QC_BASE_URL") or os.getenv("LLM_BASE_URL") or DEFAULT_BASE_URL
        model = os.getenv("QC_MODEL") or DEFAULT_QC_MODEL
    else:
        raise ValueError(f"Unknown LLM config '{config}'. Use '{CONFIG_GENERATOR}' or '{CONFIG_QC}'.")
    return LLMConfig(api_key=api_key, base_url=base_url, model=model)


def _require_api_key(config: str, api_key: str | None) -> str:
    """Return the API key or raise an actionable configuration error."""
    if api_key:
        return api_key
    prefix = "GENERATOR" if config == CONFIG_GENERATOR else "QC"
    raise ValueError(
        f"LLM_API_KEY is not set and {prefix}_API_KEY is not set. "
        "Create a .env file in the project root (see .env.example) or export the variable."
    )


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


class LLMClient:
    """OpenRouter client bound to a generator or QC configuration."""

    def __init__(self, config: str = CONFIG_GENERATOR) -> None:
        """Load the API credentials and endpoint for the requested role.

        Args:
            config: ``generator`` or ``qc``; selects the matching environment variables.
        """
        load_dotenv()
        settings = _load_config(config)
        self.config = config
        self.api_key = _require_api_key(config, settings.api_key)
        self.base_url = settings.base_url
        self.model = settings.model
        self.endpoint = f"{self.base_url}{CHAT_ENDPOINT_PATH}"

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        config: str | None = None,
    ) -> str:
        """Send a chat completion request with retries and timing logs.

        Args:
            messages: List of {"role": ..., "content": ...} messages.
            model: Model identifier to use; defaults to the client configuration.
            temperature: Sampling temperature (0.0-2.0).
            max_tokens: Maximum number of tokens to generate.
            config: Optional role override (``generator`` or ``qc``).

        Returns:
            The assistant text response.

        Raises:
            RuntimeError: If all retries are exhausted or the API returns an error.
        """
        if config is not None and config != self.config:
            settings = _load_config(config)
            api_key = _require_api_key(config, settings.api_key)
            base_url, default_model = settings.base_url, settings.model
        else:
            api_key, base_url, default_model = self.api_key, self.base_url, self.model
        model = model or default_model
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        endpoint = f"{base_url}{CHAT_ENDPOINT_PATH}"
        return self._send_with_retries(payload, headers, endpoint)

    def _send_with_retries(self, payload: dict, headers: dict, endpoint: str | None = None) -> str:
        """POST one chat completion request, retrying transient failures."""
        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            started_at = time.monotonic()
            try:
                response = requests.post(
                    endpoint or self.endpoint,
                    headers=headers,
                    json=payload,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
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
                tokens = data.get("usage", {}).get("completion_tokens", 0)
                logger.info("chat_completion ok in %.2fs (%d tokens)", elapsed, tokens)
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
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2000,
        config: str | None = None,
    ) -> dict | list:
        """Request a JSON-only response and parse it.

        Args:
            messages: Base conversation messages.
            schema_description: Human-readable JSON schema to request.
                Prepended as a system message when provided.
            model: Model identifier to use; defaults to the client configuration.
            temperature: Sampling temperature (0.0-2.0).
            max_tokens: Maximum number of tokens to generate.
            config: Optional role override (``generator`` or ``qc``).

        Returns:
            Parsed JSON object (dict or list).

        Raises:
            ValueError: If the response cannot be parsed as JSON.
        """
        model = model or self.model
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
        kwargs = {"model": model, "temperature": temperature, "max_tokens": max_tokens}
        if config is not None:
            kwargs["config"] = config
        raw = self.chat_completion(full_messages, **kwargs)
        cleaned = _strip_json_fences(raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.warning("Raw response was not valid JSON: %s", exc)
            raise ValueError(f"Could not parse model output as JSON: {raw[:500]}") from exc
