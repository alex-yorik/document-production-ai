"""Utility helpers for the Document Production AI pipeline."""

import json
import logging
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_DIR = PROJECT_ROOT / "input"
STATE_DIR = PROJECT_ROOT / "project_state"
OUTPUT_DIR = PROJECT_ROOT / "output"

DIRECTORIES = (INPUT_DIR, STATE_DIR, OUTPUT_DIR)

logger = logging.getLogger(__name__)


def ensure_directories() -> None:
    """Create required project directories if they do not exist."""
    for directory in DIRECTORIES:
        directory.mkdir(parents=True, exist_ok=True)
        logger.debug("Ensured directory: %s", directory)


def load_json(file_path: str | Path) -> list | dict:
    """Load a JSON file and return its parsed content.

    Args:
        file_path: Path to the JSON file.

    Returns:
        Parsed JSON content as a list or dict.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
    """
    path = Path(file_path)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(data: list | dict, file_path: str | Path) -> None:
    """Serialize data to a JSON file with UTF-8 encoding.

    Args:
        data: JSON-serializable object to persist.
        file_path: Destination path for the JSON file.
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    logger.debug("Saved JSON to %s", path)


def load_env() -> None:
    """Load environment variables from a project-local .env file."""
    dotenv_path = PROJECT_ROOT / ".env"
    load_dotenv(dotenv_path, override=False)
