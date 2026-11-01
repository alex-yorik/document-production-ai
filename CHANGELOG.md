# Changelog

Changes since baseline 86878d0 (2026-10-29). Entries use conventional-commit
types.

## Unreleased

### Fixed

- `fix` — K1: align README demo results with actual web run (62→72, +10) (`a1425ab`)
- `fix` — K2: unify provider facts and reduce independence claims (`7754b3b`)
- `fix` — K3: mark `input/` as synthetic dataset (EdTech SEA, Russian) (`1274cd1`)
- `fix` — K4: fix dollar sign rendering and unify input file contract (`c5daa9c`)
- `fix` — K6: update test counts and coverage to factual values (`8699138`)
- `fix` — K7: clean audit report paths and add English summary (this commit)

### Changed

- Switch generator to DeepSeek V4.1 Flash (DeepSeek direct provider) by owner decision; OpenRouter deepseek-v4-flash showed quality degradation in two web runs [c16c0cc]
- Switch generator from GPT-4o-mini to DeepSeek V4 Flash for cost efficiency [53f7202]
- `feat` — switch LLM provider from DeepSeek to OpenRouter (GPT-4o-mini + GLM-5.3-Flash) (`82db8c9`)
- `feat` — add iterative revision loop with convergence control (`ed953e6`)

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
