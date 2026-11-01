# Demo Data

Fully synthetic demo dataset for the document generation pipeline.
All companies, sources and figures are fictional — no real client data.

## Contents

- `input/company_brief.md` — brief for the fictional company Northwind Traders
  (specialty coffee retailer, expansion into Germany and Austria)
- `input/market_data.md` — synthetic market data (specialty coffee market)
- `input/methodology.md` — synthetic methodology with sourcing rules
- `expected/` — outputs produced by a real pipeline run on this dataset

## Run the Demo

From the repository root:

```bash
INPUT_DIR=demo/input REPORT_TITLE="Market Entry Report: Specialty Coffee in Germany and Austria" python run_pipeline.py
```

The pipeline reads documents from `demo/input/` (instead of the default
`input/`) and writes results to `output/Final_Report.docx` and
`output/QC_Report.md`.

The default `input/` is a separate synthetic sample (EdTech in Southeast Asia,
Russian-language brief); all companies and figures there are fictional too.

`demo/expected/` shows what a real run produced on this dataset, so you can
compare your own result with a historical baseline.

**Last updated:** 2026-11-01 | **Commit:** 6013500 | **Models:** DeepSeek V4.1 Flash (generator, DeepSeek direct), GLM-5.3-Flash (QC, OpenRouter) | **Dataset:** Northwind (English), synthetic
