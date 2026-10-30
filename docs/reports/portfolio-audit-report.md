# Журнал ИИ-assisted инженерных правок. Это не независимый аудит.

Дата: 2026-10-29
Ветка: `chore/portfolio-audit-fixes`
Стандарт: внутренний quality standard v2.1 (не публикуется).
Язык отчёта: русский (для владельца).

## 1. Baseline

Источник: `/root/audit_baseline_raw.md` (Фаза 0).

- main SHA: `86878d0d6992b99b9cd3ecbade64f02496f733bc`
- baseline-клон: `/root/baseline-clone`, HEAD = main, дерево чистое
- тег отката: `pre-portfolio-audit-fixes`
- Python 3.12.3, pytest 9.2.0, pytest-cov 7.1.0, coverage 7.17.0,
  bandit 1.9.4, gitleaks 8.30.1
- `pytest --collect-only -q` → `12 tests collected`

Сырые baseline-результаты:

```text
compileall -q src tests run_pipeline.py app.py   EXIT=0 (вывода нет)
pytest -q                                        EXIT=0  12 passed in 0.13s
pytest --cov=src --cov=run_pipeline -q           EXIT=0  12 passed, TOTAL 9%
bandit -r src run_pipeline.py app.py -ll -q      EXIT=0  находок High/Medium нет
gitleaks detect --source . --log-opts="--all" --redact
                                                 11 commits scanned, no leaks found
```

Незакоммиченные изменения, обнаруженные до работ (PRC-12), были вынесены
владельцем в отдельную ветку `wip/local-uncommitted` (коммит `592e2f5`);
main остался на `86878d0`.

## 2. Задачи PA-01 … PA-11

| Задача | Статус | Коммит | Команда проверки | Результат |
| --- | --- | --- | --- | --- |
| PA-01 — обязательные имена входных файлов (F-05) | DONE | `721e319` | `pytest tests/test_input_contract.py tests/test_input_validation.py -q` | 8 passed; полный прогон 16 passed |
| PA-02 — честная числовая проверка (F-02) | DONE | `16ebc22` | `pytest tests/test_qc_reviewer.py -q` | 7 passed; полный прогон 23 passed; `grep -rni demo src/qc_reviewer.py` пусто |
| PA-03 — единые метрики resolved (F-03/F-06) | DONE | `894ce48` | `pytest tests/test_metrics.py tests/test_metrics_consistency.py -q` | 15 passed; полный прогон 30 passed |
| PA-04 — безопасная загрузка и честный прогресс (F-07) | DONE | `b7d60a0` | `pytest tests/test_upload_utils.py -q`; smoke Streamlit на порту 8599 | 15 passed; HTTP 200; порт 8501 не трогали |
| PA-05 — markdown-таблицы как Word-таблицы (F-04) | DONE | `1ec55f1` | `pytest tests/test_document_assembler.py -q` | 7 passed; DOCX tables=1, rows=3, cols=2 |
| PA-06 — пути от STATE_DIR и env-конфиг клиента (F-18) | DONE | `0630500` | `pytest -q`; проверка путей | полный прогон зелёный; запуск из любого каталога |
| PA-07 — гигиена репозитория (F-13/F-14) | DONE | `b06126d` | project-scoped Cyrillic scan; reference scan | `cyrillic files: []`; smoke-скрипт перенесён, два dev view-скрипта удалены |
| PA-08 — стадии пайплайна и offline-тест (F-15/F-11) | DONE | `1f9331c` | offline pipeline test | тест проходит без сети и ключа |
| PA-09 — unit-тесты и coverage gate (F-12) | DONE | `c9f8b13` | `pytest --cov --cov-fail-under=80 -q` | 122 passed, coverage 92% |
| PA-10 — CI-гейты, зависимости, модульность (F-08/F-09/F-17) | DONE | `d323ecf` | `ruff check .`; `bandit`; `scripts/check_modularity.py` | всё зелёное; см. раздел 4 |
| PA-10b — механический `ruff format` | DONE | `f5f61b9` | `ruff format --check .` | 50 files already formatted |
| PA-11 — документация, security, tech debt, отчёт | DONE | этот коммит | приёмосчные grep; полный CI-00 | см. разделы 4–7 |

## 3. Изменения, требующие отдельного упоминания

### Изменённые существующие тесты (TST-02)

В `tests/test_input_validation.py` изменены 2 теста; оба изменения
owner-approved:

- `test_no_source_documents_raises` → `test_missing_required_sources_raises`:
  старое требование «кроме `methodology.md` нужен ещё `.md`» отменено решением
  Q1; тест проверяет сообщение об отсутствующих обязательных именах.
- `test_valid_dir_with_methodology_and_brief_does_not_raise` →
  `test_valid_dir_with_all_required_files_does_not_raise`: старая фикстура
  использовала `brief.md`; новый контракт требует `company_brief.md` и
  `market_data.md`.

Другие существующие тесты не переписывались.

### Подавления (5, все `BLE001`, точечные)

- `app.py` — верхнеуровневый обработчик Streamlit должен показать любую ошибку
  пайплайна.
- `src/qc_reviewer.py` — два подавления: повтор запроса и fallback на отчёт с
  нулевым score.
- `src/revision_loop.py` — сбой одной попытки не должен прерывать остальные секции.
- `src/section_generator.py` — сбой одной секции не должен прерывать отчёт.

Глобальных ignore нет.

### Owner-approved отклонения

- Q1 = B: обязательные имена `company_brief.md`, `market_data.md`,
  `methodology.md`.
- Q2 = HIGH с нормализацией значений.
- Q3: удалить dev view-скрипты; live smoke-скрипт перенести в
  `scripts/smoke_llm.py`.
- Q4: `app.py` вне coverage gate (отклонение от TST-04); UI-логика вынесена в
  `src/upload_utils.py`.
- Q5: один механический коммит `ruff format` (PA-10b).
- Q6: английский язык кода и докстрингов.
- Q7: mypy не включать.
- Q8: внутренний стандарт качества не публиковать.

Дополнительно:

- Команды выполнялись через `python3` (бинарь `python` на хосте отсутствует).
- `pytest.ini` остаётся единственным источником конфигурации pytest;
  `pyproject.toml` содержит только `[tool.coverage.*]`.
- В `pytest.ini` добавлен только маркер `live`.
- `demo/expected/` не пересобирался: нужен ключ владельца (O-01).
- Живой demo-инстанс на порту 8501 не перезапускался; после мержа владельцу
  нужно перезапустить его вручную.
- Модульность: три функции были разбиты без изменения логики —
  `app.py::show_results_page`, `src/document_assembler.py::generate_quality_report`,
  `src/llm_client.py::chat_completion`.
- Зависимости: старый единый файл требований удалён, добавлены
  `requirements-prod.txt` (4 runtime-пакета) и `requirements-dev.txt`
  (prod + pytest/pytest-cov/ruff/bandit). Транзитивные версии не считаются
  контрактом.
- `ruff` lint-фиксы внутри PA-10 (pre-approved, без изменения логики) затронули
  файлы: `app.py`, `run_pipeline.py`, `src/llm_client.py`,
  `src/outline_generator.py`, `src/qc_reviewer.py`, `src/revision_loop.py`,
  `src/section_generator.py`, `src/upload_utils.py`, `tests/test_metrics.py`,
  `tests/test_metrics_consistency.py`. Исправленные правила: `I001`, `UP015`,
  `F841`, `E501`, `W291`, `SIM109`, `SIM118`.
- `ruff` подавления и CI-гейты не содержат `|| true`, `continue-on-error` или
  `exit-zero`.
- Dockerfile/docker-compose в проекте нет, поэтому `.dockerignore` не создавался.

## 4. Сырые выводы проверок (CI-00, после PA-10)

```text
$ python3 -m compileall -q src tests run_pipeline.py app.py
COMPILE_EXIT=0

$ ruff check .
All checks passed!

$ ruff format --check .
50 files already formatted

$ bandit -r src run_pipeline.py app.py -ll -q
(вывода нет, exit 0)

$ python3 scripts/check_modularity.py
OK: all files <= 500 lines and functions <= 50 lines

$ pytest -m "not live" --cov --cov-fail-under=80 -q
TOTAL 874 52 214 29 92%
Required test coverage of 80% reached. Total coverage: 92.00%
122 passed in 3.89s

$ gitleaks detect --source . --log-opts="--all" --redact
23 commits scanned.
scanned ~233020 bytes (233.02 KB)
no leaks found
```

Coverage-разбивка последнего прогона:

```text
run_pipeline.py               113   6  14  2  92%
src/document_assembler.py     208  16  58  9  90%
src/ingestion.py               55   3  20  1  95%
src/llm_client.py              71   0  12  0 100%
src/metrics.py                 26   0   6  1  97%
src/outline_generator.py       75  13  24  7  80%
src/qc_reviewer.py            107  11  28  7  85%
src/retrieval.py               27   0   2  0 100%
src/revision_loop.py           48   0  14  0 100%
src/section_generator.py       72   1  14  1  98%
src/upload_utils.py            43   2  20  1  95%
src/utils.py                   28   0   2  0 100%
TOTAL                         874  52 214 29  92%
```

## 5. Проверка README на чистом клоне

Чистый клон ветки в `/tmp/pa11-clean`, отдельный venv, установка
`requirements-dev.txt`:

```text
$ pytest -m "not live" --cov --cov-fail-under=80 -q
122 passed in 3.75s
EXIT=0
```

Запуск без API-ключа (`DEEPSEEK_API_KEY` снят из окружения):

```text
$ python run_pipeline.py
... Stage 1: Ingestion completed. Created 13 chunks from 3 files.
... Stage 2: Retrieval ready. 13 chunks loaded.
Traceback (most recent call last):
  ...
ValueError: DEEPSEEK_API_KEY is not set. Create a .env file in the project root
(see .env.example) or export the variable.
PIPE_EXIT=1
```

Вывод понятный; перед ошибкой успевают отработать ingestion и retrieval.

## 6. Статус EVD-01

VERIFIED:

- все локальные проверки из раздела 4;
- чистый клон: pytest зелёный, запуск без ключа даёт понятную ошибку;
- push ветки в origin;
- PR #1 открыт, все проверки зелёные (источник: скриншот владельца PR #1,
  дата 2026-10-30);
- GitHub Actions отработали на PR #1: workflow CI (job `validate`) и workflow
  Quality Gates (jobs `modularity`, `security`) — Successful на `pull_request`
  и `push` (источник: скриншот владельца PR #1, дата 2026-10-30);
- имена job подтверждены живым прогоном: `validate`, `modularity`, `security`;
- бейдж CI в README ссылается на workflow `CI` (файл `.github/workflows/ci.yml`,
  ветка `main`) и подтверждён в Actions.

NOT VERIFIED:

- открытых пунктов нет.

Точные имена job для задачи владельца O-03 (значения поля `name:` / `job:`):
`validate`, `modularity`, `security`.

## 7. Baseline vs итог

| Метрика | Baseline | Итог PA-11 |
| --- | --- | --- |
| Тестов собрано | 12 | 122 |
| `pytest -q` | 12 passed | 122 passed |
| Coverage (`src/`, `run_pipeline.py`) | 9% | 92% |
| bandit High/Medium | 0 | 0 |
| gitleaks | 11 commits, no leaks | 23 commits, no leaks |
| ruff | не настроен в baseline-прогоне | `All checks passed!` |
| Формат | не проверялся | 50 files already formatted |
| Модульность | не проверялась | OK (файлы ≤ 500, функции ≤ 50) |
| Actions | не запускались | VERIFIED: PR #1 зелёный (`validate`, `modularity`, `security`) |
