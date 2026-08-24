"""Print a generated section (or all) from project_state/draft_sections.json."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils import load_json

DRAFT_SECTIONS_PATH = (
    Path(__file__).resolve().parent.parent / "project_state" / "draft_sections.json"
)


def _print_section(title: str, text: str) -> None:
    print(f"=== {title} ===")
    print(text.strip() if text else "(empty)")
    print()


def main() -> int:
    """Load draft sections and print the requested one(s)."""
    if len(sys.argv) < 2:
        print("Usage: python3 src/view_section.py <section_title | all>")
        return 1
    target = " ".join(sys.argv[1:]).strip().lower()

    try:
        sections = load_json(DRAFT_SECTIONS_PATH)
    except FileNotFoundError:
        print(f"Sections file not found at {DRAFT_SECTIONS_PATH}.")
        print("Run the pipeline first (python3 run_pipeline.py) to generate sections.")
        return 1
    except Exception as exc:
        print(f"Failed to load sections: {exc}")
        return 1

    if not isinstance(sections, dict):
        print("Invalid sections: expected a JSON object.")
        return 1

    if target == "all":
        if not sections:
            print("No sections found.")
            return 1
        for title, text in sections.items():
            _print_section(title, text)
        return 0

    found = {title: text for title, text in sections.items() if title.lower() == target}
    if not found:
        print(f"Section '{sys.argv[1]}' not found. Available sections:")
        for title in sections:
            print(f"  - {title}")
        return 1

    for title, text in found.items():
        _print_section(title, text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
