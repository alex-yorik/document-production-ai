# Technical Debt

Discovery date for open items: 2026-10-29.

## Open

- **Text-only issue resolution.** An issue counts as resolved also when it was
  rephrased or downgraded in severity. There is no semantic verification that
  the underlying claim was fixed. (2026-10-29)
- **Single demo sample.** Demo evidence is one run on one synthetic dataset; it
  is not a benchmark and has no confidence interval. (2026-10-29)
- **Same LLM family writes and reviews.** Generator and reviewer are not
  independent, so scores are indicative only. (2026-10-29)
- **Retrieval without embeddings.** Retrieval is a matching-word counter over
  chunks, not a semantic search layer. (2026-10-29)
- **mypy is not enabled.** Static typing is not part of the gate; this is an
  owner-approved decision (Q7). (2026-10-29)
- **`app.py` is outside the coverage gate.** Streamlit UI logic was extracted to
  `src/upload_utils.py` and is covered there, but `app.py` itself is not measured.
  This is an owner-approved deviation from TST-04 (Q4). (2026-10-29)
- **`demo/expected/` needs a rebuild.** The stored outputs predate the PA-02 and
  PA-05 fixes. Rebuilding requires the owner's API key (owner task O-01).
  (2026-10-29)

## Closed

- **2026-10-29 — obsolete image-todo note.** The `docs` image-todo markdown file
  was removed with `git rm`; the pending idea (an optional architecture image) is
  not blocking publication.
- **2026-10-29 — PA-01.** Required input file names are enforced:
  `company_brief.md`, `market_data.md`, `methodology.md`.
- **2026-10-29 — PA-02.** The numeric traceability check is honest: every numeric
  token in every section is checked against the sources; untraceable tokens are
  reported as HIGH issues marked `(automated check)`.
- **2026-10-29 — PA-03.** Resolved-issue metrics are unified in `src/metrics.py`;
  the QC report and pipeline metrics use the same definition.
- **2026-10-29 — PA-04.** Upload handling moved to `src/upload_utils.py`, with
  file-name sanitisation and the fake progress bar removed.
- **2026-10-29 — PA-05.** Markdown tables render as Word tables; italic inline
  markup is supported.
- **2026-10-29 — PA-06.** State paths derive from `src/utils.py::STATE_DIR`;
  client endpoint and model are configurable from the environment.
- **2026-10-29 — PA-07.** The live smoke script moved to `scripts/smoke_llm.py`;
  two unused development view scripts were removed; comments are in English.
- **2026-10-29 — PA-08.** `run_full_pipeline` is split into stages; an offline
  end-to-end pipeline test was added.
- **2026-10-29 — PA-09.** Unit tests cover all modules; the coverage gate is 80%
  (current run: 92%).
- **2026-10-29 — PA-10 / PA-10b.** CI quality gates were added, dependencies were
  split into production and dev files, the modularity check was introduced, and a
  mechanical formatting commit was applied.
