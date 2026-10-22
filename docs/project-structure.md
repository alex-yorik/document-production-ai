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
├── tests/               # offline pytest suite (12 tests)
├── .github/workflows/   # CI: pytest + bandit
└── src/                 # pipeline modules (see Architecture in README)
```
