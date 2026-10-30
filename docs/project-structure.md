# Project Structure

```text
.
├── run_pipeline.py      # pipeline entry point
├── app.py               # optional Streamlit UI
├── input/               # default input documents (synthetic)
├── demo/                # synthetic demo dataset + expected outputs
├── docs/                # images & supplementary documentation
├── output/              # generated reports (gitignored)
├── project_state/       # intermediate artifacts (gitignored)
├── scripts/
│   └── smoke_llm.py     # manual live check (needs DEEPSEEK_API_KEY, not part of the test suite)
├── tests/               # offline pytest suite
│   ├── test_config_paths.py
│   ├── test_document_assembler.py
│   ├── test_input_contract.py
│   ├── test_input_validation.py
│   ├── test_metrics.py
│   ├── test_metrics_consistency.py
│   ├── test_qc_reviewer.py
│   └── test_upload_utils.py
├── .github/workflows/   # CI: pytest + bandit
└── src/                 # pipeline modules (see Architecture in README)
    ├── document_assembler.py
    ├── ingestion.py
    ├── llm_client.py
    ├── metrics.py
    ├── outline_generator.py
    ├── qc_reviewer.py
    ├── retrieval.py
    ├── revision_loop.py
    ├── section_generator.py
    ├── upload_utils.py
    └── utils.py
```
