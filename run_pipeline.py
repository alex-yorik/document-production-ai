"""Document Production AI — pipeline entry point.

Stages:
    1. Ingestion: read input/ documents, chunk them, persist to the state directory.
    2. Retrieval: load chunks and make the keyword search layer available.
    3. Outline generation: build the report structure via LLM.
    4. Section generation: write each section with LLM + retrieval.
    5. AI Quality Review: run the QC reviewer over the generated sections.
    6. Revision loop: iteratively fix HIGH/MEDIUM issues until convergence.
    6.5. Final strict QC review: re-run the reviewer after revisions.
    7. Document assembly: export the report to DOCX in output/.
"""

import logging
import sys
from pathlib import Path

from src import ingestion, retrieval
from src.llm_client import LLMClient
from src.metrics import count_resolved_issues
from src.utils import INPUT_DIR, STATE_DIR, load_env, load_json

REQUIRED_INPUT_FILES = ("company_brief.md", "methodology.md", "market_data.md")
CHUNKS_PATH = STATE_DIR / "chunks.json"


def setup_logging() -> None:
    """Configure console logging with timestamps."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


def validate_input_dir(input_dir: Path) -> None:
    """Fail fast with actionable message if input is incomplete."""
    if not input_dir.exists():
        raise ValueError(
            f"INPUT_DIR '{input_dir}' does not exist. "
            f"Create it or run the demo: INPUT_DIR=demo/input python run_pipeline.py"
        )
    missing = [name for name in REQUIRED_INPUT_FILES if not (input_dir / name).is_file()]
    if missing:
        raise ValueError(
            f"Missing required input file(s) in '{input_dir}': {', '.join(missing)}. "
            f"Required files: {', '.join(REQUIRED_INPUT_FILES)}. "
            f"See demo/input/ for examples."
        )


def _build_metrics(qc_report: dict, qc_report_final: dict, revision_metrics: dict | None = None) -> dict:
    """Compute before/after quality metrics for the UI."""
    draft_issues = len(qc_report.get("issues", []))
    final_issues = len(qc_report_final.get("issues", []))
    resolved = count_resolved_issues(
        qc_report.get("issues", []),
        qc_report_final.get("issues", []),
    )
    metrics = {
        "draft_score": qc_report.get("overall_score", 0),
        "final_score": qc_report_final.get("overall_score", 0),
        "draft_issues": draft_issues,
        "final_issues": final_issues,
        "resolved_issues": resolved,
        "remaining_high": sum(
            1 for i in qc_report_final.get("issues", []) if isinstance(i, dict) and i.get("severity") == "HIGH"
        ),
        "remaining_issues": qc_report_final.get("issues", []),
        "resolution_rate": int(resolved / draft_issues * 100) if draft_issues > 0 else 0,
    }
    if revision_metrics is not None:
        metrics.update(
            {
                "revision_iterations": revision_metrics.get("revision_iterations", 0),
                "issues_per_iteration": revision_metrics.get("issues_per_iteration", []),
                "convergence_status": revision_metrics.get("convergence_status", "reached"),
                "improvement_score": draft_issues - final_issues,
            }
        )
    return metrics


def _stage_ingest() -> None:
    """Stage 1-2: ingest input documents and load the retrieval layer."""
    chunks = ingestion.process_documents()
    files_in = len({chunk["source_file"] for chunk in chunks})
    print(f"Stage 1: Ingestion completed. Created {len(chunks)} chunks from {files_in} files.")

    chunks = retrieval.load_chunks()
    print(f"Stage 2: Retrieval ready. {len(chunks)} chunks loaded.")


def _stage_outline(client: LLMClient) -> dict:
    """Stage 3: generate the report outline."""
    logging.info("Stage 3: Outline Generation")
    from src.outline_generator import OutlineGenerator, load_input_files

    brief, methodology, market_data = load_input_files()
    generator = OutlineGenerator(client)
    outline = generator.generate_outline(brief, methodology, market_data)

    logging.info(f"Generated outline with {len(outline['outline'])} sections")
    logging.info(f"Estimated total pages: {outline['total_estimated_pages']}")

    # Pretty print the outline to the console
    for section in outline["outline"]:
        logging.info(f"  {section['section_number']}. {section['title']}")
    return outline


def _stage_sections(client: LLMClient, outline: dict) -> tuple[dict, list, str]:
    """Stage 4: generate all report sections."""
    logging.info("Stage 4: Section Generation")
    from src.section_generator import SectionGenerator

    all_chunks = load_json(CHUNKS_PATH)

    with open(INPUT_DIR / "methodology.md", encoding="utf-8") as f:
        methodology_text = f.read()

    generator = SectionGenerator(client)
    sections = generator.generate_all_sections(outline, all_chunks, methodology_text)

    logging.info(f"Generated {len(sections)} sections")
    return sections, all_chunks, methodology_text


def _stage_review(client: LLMClient, sections: dict, outline: dict, methodology_text: str) -> tuple[object, dict]:
    """Stage 5: run the AI quality review."""
    logging.info("Stage 5: AI Quality Review")
    from src.qc_reviewer import QCReviewer

    qc_reviewer = QCReviewer(client)
    qc_report = qc_reviewer.review_sections(sections, outline, methodology_text)

    logging.info(f"QC found {len(qc_report['issues'])} issues")
    logging.info(f"  HIGH: {sum(1 for i in qc_report['issues'] if i['severity'] == 'HIGH')}")
    logging.info(f"  MEDIUM: {sum(1 for i in qc_report['issues'] if i['severity'] == 'MEDIUM')}")
    logging.info(f"  LOW: {sum(1 for i in qc_report['issues'] if i['severity'] == 'LOW')}")
    logging.info(f"Overall Score: {qc_report['overall_score']}/100")
    return qc_reviewer, qc_report


def _stage_revision(
    client: LLMClient,
    sections: dict,
    outline: dict,
    methodology_text: str,
    all_chunks: list,
    qc_reviewer,
    qc_report: dict,
) -> tuple[dict, dict, dict]:
    """Stage 6-6.5: iteratively fix issues, then run the final strict QC pass."""
    from src.revision_loop import MAX_ITERATIONS, RevisionLoop

    revision_loop = RevisionLoop(client, all_chunks, methodology_text)

    def _intermediate_qc(revised_sections: dict) -> dict:
        return qc_reviewer.review_sections(revised_sections, outline, methodology_text, strict=False)

    actionable = [i for i in qc_report.get("issues", []) if isinstance(i, dict) and i.get("severity") != "LOW"]
    logging.info(
        "Stage 6: Iterative Revision Loop (max %d iterations, %d actionable issues)",
        MAX_ITERATIONS,
        len(actionable),
    )
    sections, _last_review, revision_metrics = revision_loop.run(
        sections,
        outline,
        qc_report,
        _intermediate_qc,
        max_iterations=MAX_ITERATIONS,
    )
    logging.info(
        "Revision iterations: %d | issues per iteration: %s | convergence: %s",
        revision_metrics["revision_iterations"],
        revision_metrics["issues_per_iteration"],
        revision_metrics["convergence_status"],
    )

    logging.info("Stage 6.5: Final QC Review (post-revision, strict)")
    qc_report_final = qc_reviewer.review_sections(sections, outline, methodology_text, strict=True)

    logging.info(f"Final QC Score: {qc_report_final['overall_score']}/100")
    logging.info(f"Final issues: {len(qc_report_final['issues'])}")
    logging.info(f"  HIGH: {sum(1 for i in qc_report_final['issues'] if i['severity'] == 'HIGH')}")
    logging.info(f"  MEDIUM: {sum(1 for i in qc_report_final['issues'] if i['severity'] == 'MEDIUM')}")
    logging.info(f"  LOW: {sum(1 for i in qc_report_final['issues'] if i['severity'] == 'LOW')}")

    initial_score = qc_report["overall_score"]
    final_score = qc_report_final["overall_score"]
    initial_issues = len(qc_report["issues"])
    resolved_issues = count_resolved_issues(qc_report["issues"], qc_report_final["issues"])

    logging.info(f"Quality Improvement: {initial_score} → {final_score} (+{final_score - initial_score})")
    logging.info(f"Issues Resolved: {resolved_issues}/{initial_issues}")

    # IMPORTANT: at most MAX_ITERATIONS revision passes, then one final strict QC.
    # If HIGH issues remain after that, report them as "known limitations".
    if qc_report_final["issues"]:
        remaining_high = [i for i in qc_report_final["issues"] if i["severity"] == "HIGH"]
        if remaining_high:
            logging.warning(f"{len(remaining_high)} HIGH issues remain after revision — marked as known limitations")
    return sections, qc_report_final, revision_metrics


def _stage_assemble(
    sections: dict,
    outline: dict,
    qc_report: dict,
    qc_report_final: dict,
    revision_metrics: dict,
) -> dict:
    """Stage 7: assemble the DOCX report and QC markdown, then build metrics."""
    logging.info("Stage 7: Document Assembly")
    from src.document_assembler import DocumentAssembler

    assembler = DocumentAssembler()
    doc_path = assembler.assemble_document(sections, outline, qc_report_final)  # use the final report
    qc_report_path = assembler.generate_quality_report(qc_report, qc_report_final)  # pass both for comparison

    logging.info(f"Final report saved to: {doc_path}")
    logging.info(f"QC report saved to: {qc_report_path}")
    logging.info("Pipeline completed successfully!")

    return _build_metrics(qc_report, qc_report_final, revision_metrics)


def run_full_pipeline() -> dict:
    """Run the full pipeline and return metrics for the UI.

    Returns:
        dict with keys: draft_score, final_score, draft_issues, final_issues,
        resolved_issues, remaining_high, remaining_issues, resolution_rate,
        revision_iterations, issues_per_iteration, convergence_status,
        improvement_score.
    """
    setup_logging()
    load_env()
    validate_input_dir(INPUT_DIR)

    _stage_ingest()

    client = LLMClient()
    outline = _stage_outline(client)
    sections, all_chunks, methodology_text = _stage_sections(client, outline)
    qc_reviewer, qc_report = _stage_review(client, sections, outline, methodology_text)
    sections, qc_report_final, revision_metrics = _stage_revision(
        client, sections, outline, methodology_text, all_chunks, qc_reviewer, qc_report
    )
    return _stage_assemble(sections, outline, qc_report, qc_report_final, revision_metrics)


def main() -> int:
    """Run the full pipeline and return a process exit code."""
    run_full_pipeline()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
