"""Assemble the final DOCX report and a professional markdown QC report."""

import logging
import os
import re
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

from src.utils import OUTPUT_DIR

logger = logging.getLogger(__name__)

FINAL_REPORT_PATH = OUTPUT_DIR / "Final_Report.docx"
QC_REPORT_PATH = OUTPUT_DIR / "QC_Report.md"

TITLE = "Market Entry Report: EdTech in Southeast Asia"
SUBTITLE = "Prepared by AI Document Production System"

BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*)")
BULLET_PATTERN = re.compile(r"^\s*[-*]\s+(.*)")
NUMBERED_PATTERN = re.compile(r"^\s*\d+[.)]\s+(.*)")
TABLE_SEPARATOR_PATTERN = re.compile(r"^:?-{3,}:?$")

CHARS_PER_PAGE = 2500


class DocumentAssembler:
    """Build the final DOCX report and the QC markdown report in output/."""

    def __init__(self) -> None:
        self.output_dir = OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def assemble_document(self, sections: dict, outline: dict, qc_report: dict) -> str:
        """Render sections into a styled DOCX and save it to output/Final_Report.docx.

        Returns:
            Path to the saved DOCX file.
        """
        doc = Document()
        self._add_title_page(doc, qc_report)

        outline_sections = outline.get("outline", []) if isinstance(outline, dict) else []
        for idx, section in enumerate(outline_sections):
            title = section.get("title", f"Section {idx + 1}")
            text = sections.get(title, "") if isinstance(sections, dict) else ""
            if not text:
                logger.warning("No content found for section: %s", title)
                placeholder = doc.add_paragraph()
                placeholder.add_run(f"[{title} — content pending]").italic = True
                continue
            self._render_markdown(doc, text)

        doc.save(FINAL_REPORT_PATH)

        char_count = sum(len(t) for t in sections.values())
        pages_estimate = max(1, char_count // CHARS_PER_PAGE)
        size_kb = os.path.getsize(FINAL_REPORT_PATH) / 1024
        logger.info(
            "Assembled document: ~%d pages, %.1f KB -> %s",
            pages_estimate, size_kb, FINAL_REPORT_PATH,
        )
        return str(FINAL_REPORT_PATH)

    def _add_title_page(self, doc: Document, qc_report: dict) -> None:
        for _ in range(6):
            doc.add_paragraph()

        title_p = doc.add_paragraph()
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title_p.add_run(TITLE)
        title_run.bold = True
        title_run.font.size = Pt(24)

        subtitle_p = doc.add_paragraph()
        subtitle_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        subtitle_p.add_run(SUBTITLE).font.size = Pt(14)

        date_p = doc.add_paragraph()
        date_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        date_p.add_run(date.today().strftime("%B %d, %Y")).font.size = Pt(12)

        if isinstance(qc_report, dict) and qc_report.get("overall_score") is not None:
            qc_p = doc.add_paragraph()
            qc_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            qc_p.add_run(f"AI Quality Score: {qc_report.get('overall_score')}/100").font.size = Pt(11)

        doc.add_page_break()

    def _render_markdown(self, doc: Document, text: str) -> None:
        for raw_line in text.splitlines():
            stripped = raw_line.strip()
            if not stripped or stripped in ("---", "***", "___"):
                continue
            if stripped.startswith("|"):
                self._render_table_row(doc, stripped)
                continue
            heading = HEADING_PATTERN.match(stripped)
            if heading:
                level = min(len(heading.group(1)), 4)
                self._add_heading(doc, heading.group(2).strip(), level)
                continue
            bullet = BULLET_PATTERN.match(stripped)
            if bullet:
                self._add_paragraph_with_bold(doc, bullet.group(1).strip(), style="List Bullet")
                continue
            numbered = NUMBERED_PATTERN.match(stripped)
            if numbered:
                self._add_paragraph_with_bold(doc, numbered.group(1).strip(), style="List Number")
                continue
            self._add_paragraph_with_bold(doc, stripped)

    def _render_table_row(self, doc: Document, line: str) -> None:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if cells and all(TABLE_SEPARATOR_PATTERN.match(cell) for cell in cells):
            return
        self._add_paragraph_with_bold(doc, " | ".join(cells))

    def _add_heading(self, doc: Document, title: str, level: int) -> None:
        heading = doc.add_heading("", level=level)
        run = heading.add_run(title.replace("**", ""))
        run.bold = True
        run.font.color.rgb = RGBColor(0x1F, 0x3B, 0x73)

    def _add_paragraph_with_bold(
        self, doc: Document, text: str, style: str | None = None
    ) -> None:
        paragraph = doc.add_paragraph(style=style) if style else doc.add_paragraph()
        position = 0
        for match in BOLD_PATTERN.finditer(text):
            if match.start() > position:
                paragraph.add_run(text[position:match.start()])
            bold_run = paragraph.add_run(match.group(1))
            bold_run.bold = True
            position = match.end()
        if position < len(text):
            paragraph.add_run(text[position:])

    @staticmethod
    def _count_severities(issues: list) -> dict:
        counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for issue in issues:
            severity = issue.get("severity") if isinstance(issue, dict) else None
            if severity in counts:
                counts[severity] += 1
        return counts

    @staticmethod
    def _render_severity_block(lines: list, issues: list, severity: str) -> None:
        lines += [f"### {severity} Severity", ""]
        severity_issues = [
            issue for issue in issues
            if isinstance(issue, dict) and issue.get("severity") == severity
        ]
        if not severity_issues:
            lines += ["None.", ""]
            return
        for idx, issue in enumerate(severity_issues, start=1):
            lines += [
                f"{idx}. {issue.get('section', 'N/A')}: {issue.get('description', 'N/A')}",
                f"- Location: {issue.get('location', 'N/A')}",
                f"- Suggestion: {issue.get('suggestion', 'N/A')}",
                "",
            ]

    @staticmethod
    def _render_revision_actions(lines: list, qc_report: dict, counts: dict) -> None:
        lines += ["## Revision Actions Taken", ""]
        revisions = qc_report.get("revisions")
        if isinstance(revisions, list) and revisions:
            lines += [f"- {item}" for item in revisions]
            return
        if counts["HIGH"]:
            for issue in qc_report.get("issues", []):
                if isinstance(issue, dict) and issue.get("severity") == "HIGH":
                    lines.append(
                        f"- {issue.get('section', 'N/A')}: Fixed {issue.get('issue_type', 'issue')} issue"
                    )
            return
        lines.append("- No HIGH severity issues found; no revision was required.")

    def generate_quality_report(self, qc_report: dict) -> str:
        """Write a readable markdown QC report to output/QC_Report.md.

        Returns:
            Path to the saved QC report file.
        """
        if not isinstance(qc_report, dict):
            logger.warning("QC report is not a dict; writing an empty report")
            qc_report = {}
        issues = qc_report.get("issues")
        if not isinstance(issues, list):
            issues = []
        counts = self._count_severities(issues)

        lines: list[str] = [
            "# Quality Control Report",
            "",
            "## Summary",
            "",
            f"Overall Score: {qc_report.get('overall_score', 0)}/100",
            f"Total Issues: {len(issues)}",
            "",
            "## Issues by Severity",
            "",
        ]
        lines += [f"- {sev}: {counts[sev]}" for sev in ("HIGH", "MEDIUM", "LOW")]
        lines += ["", "## Detailed Issues", ""]
        for severity in ("HIGH", "MEDIUM", "LOW"):
            self._render_severity_block(lines, issues, severity)
        self._render_revision_actions(lines, qc_report, counts)
        lines.append("")

        markdown = "\n".join(lines)
        QC_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        Path(QC_REPORT_PATH).write_text(markdown, encoding="utf-8")
        logger.info(
            "QC report written to %s (%d bytes)",
            QC_REPORT_PATH, QC_REPORT_PATH.stat().st_size,
        )
        return str(QC_REPORT_PATH)
