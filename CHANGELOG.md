# Changelog

All entries correspond to commits on `chore/portfolio-audit-fixes` since
`main` (baseline `86878d0`, 2026-10-29). Entries use conventional-commit types.

## Unreleased

### Features

- `feat` — PA-01: enforce required input file names (`721e319`)
- `feat` — PA-02: honest numeric traceability check (`16ebc22`)
- `feat` — PA-03: unified resolved metrics in `src/metrics.py` (`894ce48`)
- `feat` — PA-04: safe upload handling and honest progress in the Streamlit UI (`b7d60a0`)
- `feat` — PA-05: render markdown tables as Word tables, support italic (`1ec55f1`)
- `feat` — PA-06: paths from `STATE_DIR`, environment config in client init (`0630500`)
- `feat` — PA-08: split `run_full_pipeline` into stages, offline pipeline test (`1f9331c`)

### Refactor

- `refactor` — PA-07: repo hygiene — smoke script, remove dev utilities, English comments (`b06126d`)

### Tests

- `test` — PA-09: unit tests for all modules, coverage gate 80% (`c9f8b13`)

### Build / CI

- `ci` — PA-10: CI quality gates, split dependencies, modularity check (`d323ecf`)

### Style

- `style` — PA-10b: mechanical `ruff format` (`f5f61b9`)

### Documentation

- `docs` — PA-11: honest documentation, security and tech-debt docs, audit report (this commit)
