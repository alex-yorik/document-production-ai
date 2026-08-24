"""Pretty-print the generated outline from project_state/outline.json."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils import load_json

OUTLINE_PATH = Path(__file__).resolve().parent.parent / "project_state" / "outline.json"


def main() -> int:
    """Load the outline JSON and print it in a human-readable format."""
    try:
        data = load_json(OUTLINE_PATH)
    except FileNotFoundError:
        print(f"Outline file not found at {OUTLINE_PATH}.")
        print("Run the pipeline first (python3 run_pipeline.py) to generate it.")
        return 1
    except Exception as exc:
        print(f"Failed to load outline: {exc}")
        return 1

    sections = data.get("outline", [])
    if not isinstance(sections, list):
        print("Invalid outline: 'outline' is not a list.")
        return 1

    print("=== OUTLINE ===")
    for section in sections:
        if not isinstance(section, dict):
            continue
        print(f"\n{section.get('section_number', '?')}.")
        print(section.get("title", "Untitled"))
        print(f"Description: {section.get('description', 'N/A')}")
        print("Key Points:")
        for point in section.get("key_points", []) or []:
            print(f"  • {point}")
        print(f"Estimated: {section.get('estimated_length', 'N/A')}")

    print(f"\nTotal estimated pages: {data.get('total_estimated_pages', 'N/A')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
