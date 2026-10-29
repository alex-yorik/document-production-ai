# Architecture

This document describes how the current code moves data through the pipeline.
It reflects the implementation on this branch; it does not describe planned
features.

## Stage flow

```text
input/*.md|*.txt
   │
   ▼
1. Ingestion            src/ingestion.py
   │  chunk + persist
   ▼
project_state/chunks.json
   │
   ├──────────────► 2. Retrieval (read-only)   src/retrieval.py
   │                    keyword match over chunks
   ▼
3. Outline generation   src/outline_generator.py
   │  LLM JSON response
   ▼
project_state/outline.json
project_state/outline_raw_response.txt
   │
   ▼
4. Section generation   src/section_generator.py
   │  LLM + retrieval context per section
   ▼
project_state/draft_sections.json
   │
   ▼
5. QC review             src/qc_reviewer.py
   │  LLM review + deterministic numeric check
   ▼
project_state/qc_report.json
   │
   ▼
6. Revision loop         src/revision_loop.py
   │  regenerate HIGH-issue sections (one pass)
   ▼
project_state/draft_sections.json (updated)
   │
   ▼
6.5 Final QC review      src/qc_reviewer.py
   │  same reviewer, post-revision snapshot
   ▼
project_state/qc_report.json (last write wins)
   │
   ▼
7. Assembly              src/document_assembler.py
   │  DOCX + markdown report
   ▼
output/Final_Report.docx
output/QC_Report.md
```

## Storage

All intermediate files live in `project_state/`; final deliverables live in
`output/`. Both directories are gitignored and local to the machine.

- `project_state/chunks.json` — list of chunks, each with `source_file`,
  `chunk_index`, and `text`. Written by ingestion, read by retrieval and the QC
  reviewer.
- `project_state/outline.json` — normalized outline: section numbers, titles,
  descriptions, key points, estimated length, and total estimated pages.
- `project_state/outline_raw_response.txt` — raw outline response for debugging.
- `project_state/draft_sections.json` — generated section markdown, updated by
  the revision loop.
- `project_state/qc_report.json` — the most recent normalized QC review. The
  draft review is written first, then the post-revision review overwrites the
  same path.
- `output/Final_Report.docx` — assembled DOCX built from the final sections and
  the final QC report.
- `output/QC_Report.md` — before/after comparison with revision actions.

Paths are built from `src/utils.py::STATE_DIR` and `OUTPUT_DIR`, which are
absolute and derived from the repository root, so the pipeline can be launched
from any working directory. `INPUT_DIR` defaults to `input/` and can be
overridden with the `INPUT_DIR` environment variable.

## Key decisions

- **Fixed input contract.** Three files are required: `company_brief.md`,
  `market_data.md`, `methodology.md`. Additional `.md`/`.txt` files are still
  ingested and retrieved, but the required names are checked before any LLM call.
- **Non-recursive revision.** Only one extra QC pass runs after revisions.
  Remaining HIGH issues are reported, not hidden or looped on indefinitely.
- **Two-part QC.** The LLM reviewer judges traceability, forecasts and tone; the
  deterministic numeric check independently flags numeric tokens absent from the
  source chunks. The check is token-based and severity is HIGH.
- **Single LLM client.** `src/llm_client.py` is a minimal OpenAI-compatible
  client for DeepSeek with retries, timing logs, JSON-fence stripping, and a
  bounded number of attempts. There is no provider abstraction.
- **Offline tests.** The pipeline is split into stages in `run_pipeline.py`, and
  the test suite replaces the client with a fake and patches module-level paths,
  so the full pipeline can run without network access.
- **Local-only UI.** `app.py` is an optional Streamlit UI; upload handling and
  the deterministic helpers live in `src/upload_utils.py`.
