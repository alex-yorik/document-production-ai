"""Document Production AI — pipeline entry point.

Stages:
    1. Ingestion: read input/ documents, chunk them, persist to project_state/.
    2. Retrieval: load chunks and make the keyword search layer available.
    3. Outline generation: build the report structure via LLM.
    4. Section generation: write each section with LLM + retrieval.
    5. AI Quality Review: run the QC reviewer over the generated sections.
    6. Revision loop: fix HIGH severity issues by regenerating sections.
    7. Document assembly: export the report to DOCX in output/.
"""

import logging
import sys

from src import ingestion, retrieval
from src.utils import load_env, load_json


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

    # --- Stage 4: Section Generation -----------------------------------------
    logging.info("Stage 4: Section Generation")
    from src.section_generator import SectionGenerator

    # Загружаем chunks
    all_chunks = load_json("project_state/chunks.json")

    # Загружаем methodology
    with open("input/methodology.md", "r", encoding="utf-8") as f:
        methodology_text = f.read()

    # Генерируем все разделы
    generator = SectionGenerator(client)
    sections = generator.generate_all_sections(outline, all_chunks, methodology_text)

    logging.info(f"Generated {len(sections)} sections")

    # --- Stage 5: AI Quality Review -----------------------------------------
    logging.info("Stage 5: AI Quality Review")
    from src.qc_reviewer import QCReviewer

    qc_reviewer = QCReviewer(client)
    qc_report = qc_reviewer.review_sections(sections, outline, methodology_text)

    logging.info(f"QC found {len(qc_report['issues'])} issues")
    logging.info(f"  HIGH: {sum(1 for i in qc_report['issues'] if i['severity'] == 'HIGH')}")
    logging.info(f"  MEDIUM: {sum(1 for i in qc_report['issues'] if i['severity'] == 'MEDIUM')}")
    logging.info(f"  LOW: {sum(1 for i in qc_report['issues'] if i['severity'] == 'LOW')}")
    logging.info(f"Overall Score: {qc_report['overall_score']}/100")

    # --- Stage 6: Revision Loop (if HIGH issues found) ----------------------
    high_issues = qc_reviewer.get_high_severity_issues(qc_report)
    if high_issues:
        logging.info(f"Stage 6: Revision Loop - fixing {len(high_issues)} HIGH issues")
        from src.revision_loop import RevisionLoop

        revision_loop = RevisionLoop(client, all_chunks, methodology_text)
        sections = revision_loop.fix_sections(sections, outline, high_issues)
        logging.info("Revision complete. Sections updated.")
    else:
        logging.info("Stage 6: No HIGH issues found. Skipping revision.")

    # --- Stage 7: Document Assembly ------------------------------------------
    logging.info("Stage 7: Document Assembly")
    from src.document_assembler import DocumentAssembler

    assembler = DocumentAssembler()
    doc_path = assembler.assemble_document(sections, outline, qc_report)
    qc_report_path = assembler.generate_quality_report(qc_report)

    logging.info(f"Final report saved to: {doc_path}")
    logging.info(f"QC report saved to: {qc_report_path}")
    logging.info("Pipeline completed successfully!")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
