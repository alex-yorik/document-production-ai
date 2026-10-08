# AI Document Production & Quality Control

A working prototype that turns source documents into a structured DOCX report —
and then makes the AI critique and improve its own output before delivery.

![Pipeline](docs/pipeline.png)

## Overview

- **Input:** 2–5 markdown/text documents (brief, market data, methodology)
- **Output:** styled DOCX report + QC report with before/after metrics
- **Status:** working prototype, not production-ready

## Problem

LLMs generate fluent text but frequently hallucinate: invented figures,
unsupported claims, statements that are not traceable to sources. In business
documents — market reports, briefings — this is a direct credibility risk,
and manual review does not scale.

## Solution

The pipeline pairs a generator with a dedicated QC reviewer. Every section is
checked against the source material. HIGH-severity issues trigger an automated
revision loop. Remaining issues are surfaced for human review — the system
does not blindly approve its own output.

## How It Works

1. **Ingestion** — source documents are chunked and persisted
2. **Retrieval** — lightweight keyword search over chunks
3. **Outline Generation** — LLM builds a 5–6 section report structure
4. **Section Generation** — each section written with LLM + retrieval context
5. **AI Quality Review** — QC reviewer scores sections, reports issues by severity
6. **Revision Loop** — sections with HIGH issues are regenerated (max 1 extra QC pass)
7. **Document Assembly** — styled DOCX + QC report

## Architecture

```text
run_pipeline.py            # pipeline entry point
app.py                     # optional Streamlit web UI
src/
├── ingestion.py           # chunk source documents
├── retrieval.py           # keyword search layer
├── outline_generator.py   # LLM report structure
├── section_generator.py   # LLM sections with retrieval
├── qc_reviewer.py         # severity-scored issue detection
├── revision_loop.py       # regenerate sections with HIGH issues
├── document_assembler.py  # DOCX + QC report export
├── llm_client.py          # DeepSeek API client
└── utils.py               # paths, env, JSON helpers
```

## Quality Control

The QC reviewer checks each section for:

- factual traceability — every number and claim must come from the source documents
- unsupported forecasts and derived calculations
- tone and structure appropriate for a C-level audience

Issues are graded HIGH / MEDIUM / LOW with an overall score (0–100).

Demo run results (real, unedited):

| Metric       | Draft           | Final (after revision)   |
| ------------ | --------------- | ------------------------ |
| Quality score | 62/100         | 72/100                   |
| Issues       | 13 (9 HIGH)     | 12 (5 HIGH, 7 MEDIUM)    |

![QC report](docs/qc-report.png)

## Revision Loop

Sections flagged with HIGH-severity issues are regenerated with the issues and
source context injected into the prompt. One extra QC pass runs after revision;
the loop deliberately does not recurse. Remaining HIGH issues are surfaced for
human review, not hidden.

![Final document](docs/final-document.png)

## Output

- `output/Final_Report.docx` — styled report (title page, headings, tables,
  bullets, QC score)
- `output/QC_Report.md` — before/after issue comparison with revision actions

## Demo

`demo/` contains a fully synthetic dataset — a fictional company
("Northwind Traders", specialty coffee expansion into Germany and Austria) —
plus `demo/expected/` with the outputs of a real pipeline run. No real client
data is used anywhere in this repository.

## Tech Stack

- Python 3.12
- DeepSeek API (LLM)
- python-docx (DOCX assembly)
- Streamlit (optional web UI)
- python-dotenv

## Project Structure

```text
.
├── run_pipeline.py      # pipeline entry point
├── app.py               # optional Streamlit UI
├── input/               # default input documents (synthetic)
├── demo/                # synthetic demo dataset + expected outputs
├── docs/                # images
├── output/              # generated reports (gitignored)
├── project_state/       # intermediate artifacts (gitignored)
└── src/                 # pipeline modules (see Architecture)
```

## Installation

```bash
git clone https://github.com/alex-yorik/document-production-ai.git
cd document-production-ai
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Configuration

Copy `.env.example` to `.env` and set your API key:

```bash
DEEPSEEK_API_KEY=your_api_key_here
```

`.env` is gitignored and is never committed. Optional settings (endpoint,
model, report title) are documented in `.env.example`.

## Running the Demo

```bash
python run_pipeline.py
```

or, using the synthetic dataset from `demo/`:

```bash
INPUT_DIR=demo/input REPORT_TITLE="Market Entry Report: Specialty Coffee in Germany and Austria" python run_pipeline.py
```

Processing takes ~2–4 minutes (LLM calls). Results are written to
`output/Final_Report.docx` and `output/QC_Report.md`, comparable to
`demo/expected/`.

## Limitations

This is a working prototype. Current limitations include:

- retrieval is intentionally lightweight;
- document quality depends on source material;
- AI-generated content requires human review;
- the system is not yet designed for high-volume production;
- authentication and multi-user management are outside the current scope.

## Future Improvements

- embeddings-based retrieval with relevance ranking
- configurable document schemas beyond market entry reports
- PDF export
- human-in-the-loop review step before final assembly

## License

**LICENSE DECISION REQUIRED** — no license has been selected yet. This must be
decided before the repository is made public. All rights reserved until then.
