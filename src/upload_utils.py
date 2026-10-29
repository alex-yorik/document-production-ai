"""Pure helpers for handling files uploaded through the Streamlit UI."""

from pathlib import Path

from src.utils import INPUT_DIR, PROJECT_ROOT

ALLOWED_EXTENSIONS = {".md", ".txt"}
MIN_UPLOAD_FILES = 2
MAX_UPLOAD_FILES = 5
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
REQUIRED_UPLOAD_FILE = "methodology.md"


def validate_uploads(uploaded_files) -> str | None:
    """Validate uploaded source files before running the pipeline.

    Returns an error message, or None if the uploads are valid.
    """
    if not uploaded_files or not (
        MIN_UPLOAD_FILES <= len(uploaded_files) <= MAX_UPLOAD_FILES
    ):
        return (
            f"Upload {MIN_UPLOAD_FILES} to {MAX_UPLOAD_FILES} files "
            "(.md or .txt)."
        )

    total_bytes = sum(len(f.getvalue()) for f in uploaded_files)
    if total_bytes > MAX_UPLOAD_BYTES:
        total_mb = total_bytes / (1024 * 1024)
        return (
            f"Total upload size is {total_mb:.1f} MB — the limit is 10 MB. "
            "Remove a file or reduce its size."
        )

    names = {Path(f.name).name for f in uploaded_files}
    if REQUIRED_UPLOAD_FILE not in names:
        return (
            f"Missing required file: {REQUIRED_UPLOAD_FILE}. "
            "Include methodology.md among the uploaded files. "
            "See demo/input/ for examples."
        )

    return None


def save_uploaded_files(uploaded_files, input_dir: str | Path = INPUT_DIR) -> None:
    """Validate file names and save uploads into the input directory.

    File names are reduced to their basename to prevent path traversal, and
    only .md/.txt extensions are accepted.
    """
    pending = []
    for uploaded_file in uploaded_files:
        name = Path(uploaded_file.name).name
        if Path(name).suffix.lower() not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type: '{uploaded_file.name}'. "
                "Only .md and .txt files are allowed."
            )
        pending.append((name, uploaded_file))

    clean_input_dir(input_dir)
    target_dir = Path(input_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    for name, uploaded_file in pending:
        (target_dir / name).write_bytes(uploaded_file.getvalue())


def clean_input_dir(input_dir: str | Path = INPUT_DIR) -> None:
    """Remove stale .md/.txt files from the input directory.

    Refuses to run when the target is the project root or lives inside demo/.
    """
    target = Path(input_dir).resolve()
    project_root = PROJECT_ROOT.resolve()
    demo_dir = (project_root / "demo").resolve()

    if target == project_root or target == demo_dir or demo_dir in target.parents:
        raise ValueError(
            f"Refusing to clean INPUT_DIR '{target}': it is the project root "
            "or inside demo/."
        )

    if not target.exists():
        return

    for path in target.iterdir():
        if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS:
            path.unlink()


def format_delta(value: int) -> str:
    """Format a signed delta for the metrics display."""
    return f"+{value}" if value > 0 else str(value)
