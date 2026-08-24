"""Document Production AI — pipeline entry point.

Stages:
    1. Ingestion: read input/ documents, chunk them, persist to project_state/.
    2. Retrieval: load chunks and make the keyword search layer available.
    3. Outline generation: build the report structure via LLM.
    4. (TODO) Section generation: write each section with LLM + retrieval.
    5. (TODO) Export: convert the report to DOCX in output/.
"""

import logging
import sys

from src import ingestion, retrieval
from src.utils import load_env


def setup_logging() -> None:
    """Configure console logging with timestamps."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


def main() -> int:
    """Run the full pipeline and return a process exit code."""
    setup_logging()
    load_env()

    log = logging.getLogger("run_pipeline")

    # --- Stage 1: Ingestion -------------------------------------------------
    chunks = ingestion.process_documents()
    files_in = len({chunk["source_file"] for chunk in chunks})
    print(f"Stage 1: Ingestion completed. Created {len(chunks)} chunks from {files_in} files.")

    # --- Stage 2: Retrieval layer -------------------------------------------
    chunks = retrieval.load_chunks()
    print(f"Stage 2: Retrieval ready. {len(chunks)} chunks loaded.")

    # --- Stage 3: Outline Generation -----------------------------------------
    logging.info("Stage 3: Outline Generation")
    from src.llm_client import DeepSeekClient
    from src.outline_generator import OutlineGenerator, load_input_files

    client = DeepSeekClient()
    brief, methodology, market_data = load_input_files()
    generator = OutlineGenerator(client)
    outline = generator.generate_outline(brief, methodology, market_data)

    logging.info(f"Generated outline with {len(outline['outline'])} sections")
    logging.info(f"Estimated total pages: {outline['total_estimated_pages']}")

    # Pretty print outline в консоль
    for section in outline['outline']:
        logging.info(f"  {section['section_number']}. {section['title']}")

    # --- Stage 4: (TODO) Section generation ---------------------------------
    # log.info("Stage 4: Section generation - coming next")

    # --- Stage 5: (TODO) Export to DOCX -------------------------------------
    # log.info("Stage 5: Export pending")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
