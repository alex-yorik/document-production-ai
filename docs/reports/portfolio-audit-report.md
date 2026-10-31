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

## K0. Baseline и проверка того, что аудит не смог проверить

Дата: 2026-10-31
Ветка: `chore/publication-fixes` (от актуальной `main`)
Стандарт: quality standard v2.1
Тег отката: `pre-publication-fixes` → `1b696126657c21579f4c9ccb6441f09343c2306d`
(отправлен в origin, подтверждён `git ls-remote --tags`)

Исходная `main`: `1b696126657c21579f4c9ccb6441f09343c2306d`
(merge PR #2 `chore/llm-provider-and-architecture`).

Окружение: Python 3.12.3, чистый venv `/tmp/audit-venv` из
`requirements-dev.txt`: pytest 9.2.0, pytest-cov 7.1.0, coverage 7.17.0,
ruff 0.17.3, bandit 1.9.4, gitleaks 8.30.1.

### K0.1 Сводная таблица

| № | Пункт | Статус | Команда(ы) | Ключевой сырой результат |
| --- | --- | --- | --- | --- |
| 1 | Подготовка: ветка + тег отката | VERIFIED | `git checkout main && git pull`; `git checkout -b chore/publication-fixes`; `git tag pre-publication-fixes && git push origin pre-publication-fixes` | main `1b69612`; тег создан и есть в origin |
| 2 | Baseline тестов и coverage | VERIFIED (чистый checkout) / NOT VERIFIED (с локальным `.env`) | `pytest -m "not live" --cov --cov-report=term-missing --cov-fail-under=80 -q` | без `.env`: `125 passed`, 91.21%; с локальным `.env`: `5 failed, 120 passed`, 90.95% (см. K0.2) |
| 3 | ruff / bandit / modularity | VERIFIED | `ruff check .`; `bandit -r src run_pipeline.py app.py -ll -q`; `python scripts/check_modularity.py` | `All checks passed!`; bandit exit 0; `OK: all files <= 500 lines and functions <= 50 lines` |
| 4 | История git (mirror) + gitleaks + input/demo | VERIFIED | `git clone --mirror ...`; `gitleaks detect --source . --log-opts="--all" --redact -v`; `git log --all --oneline -- input demo`; `git log --all --oneline -- '*.docx' '.env*' '*.pem'` | gitleaks: `31 commits scanned`, `no leaks found`; в истории только `.env.example` и `demo/expected/Final_Report.docx`, реальных `.env`/`.pem`/`.key` нет |
| 5 | Упоминания DeepSeek | VERIFIED (найдены и локализованы) | `grep -rn "DEEPSEEK" . --exclude-dir=.git`; `grep -rniE "deepseek" . --exclude-dir=.git` | 6 файлов, см. K0.5; код и `.env.example` уже на OpenRouter |
| 6 | Скриншоты | VERIFIED | визуальный просмотр 5 PNG | личных данных, ключей и абсолютных путей нет; есть расхождения цифр между скриншотами/README, см. K0.6 |
| 7 | Документы (`ARCHITECTURE.md`, `docs/project-structure.md`, `input/`, `demo/input/`) | VERIFIED (прочитаны) / есть устаревшие утверждения | прочитаны целиком | DeepSeek/`DEEPSEEK_API_KEY` устарели; список тестов неполный; `input/*.md` без пометки synthetic, см. K0.7 |

### K0.2 Baseline тестов (сырой вывод)

Подсчёт тестов:

```text
find tests -name "test_*.py" | wc -l            → 16
grep -rhE "^\s*(async )?def test_" tests | wc -l → 109
```

`pytest` собирает 125 тестов благодаря параметризации.

Прогон в чистом checkout (локальный `.env` временно убран, затем возвращён):

```text
........................................................................ [ 57%]
.....................................................                    [100%]

Name                        Stmts   Miss Branch BrPart  Cover   Missing
-----------------------------------------------------------------------
run_pipeline.py               121      6     14      2    93%   185-187, 236-237, 241
src/__init__.py                 1      0      0      0   100%
src/document_assembler.py     208     16     58      9    90%   53-56, 91->96, 126-128, 143-145, 170->172, 213-214, 216-217, 219, 221
src/ingestion.py               55      3     20      1    95%   60->66, 93-95
src/llm_client.py             105      9     20      3    89%   44-49, 125-127, 222
src/metrics.py                 26      0      6      1    97%   34->33
src/outline_generator.py       75     13     24      7    80%   96-97, 100-101, 112-113, 116, 124, 157, 162-170
src/qc_reviewer.py            107     11     28      7    85%   134, 179-180, 182-183, 191->189, 235-238, 244, 247
src/retrieval.py               27      0      2      0   100%
src/revision_loop.py           48      0     14      0   100%
src/section_generator.py       72      1     14      1    98%   191
src/upload_utils.py            43      1     20      1    97%   72
src/utils.py                   28      0      2      0   100%
-----------------------------------------------------------------------
TOTAL                         916     60    222     32    91%
Required test coverage of 80% reached. Total coverage: 91.21%
125 passed in 11.36s
```

Прогон на рабочем хосте без изоляции окружения (локальный `.env` присутствует):

```text
5 failed, 120 passed in 15.23s
TOTAL                         916     62    222     33    91%
Required test coverage of 80% reached. Total coverage: 90.95%

FAILED tests/test_app_state.py::test_pipeline_exception_shows_error_and_keeps_generate_button_active
FAILED tests/test_config_paths.py::test_client_reads_env_after_module_import
FAILED tests/test_config_paths.py::test_model_none_uses_instance_model
FAILED tests/test_llm_client.py::test_init_requires_api_key
FAILED tests/test_llm_client.py::test_chat_completion_success
```

Причина red-прогона: в рабочем каталоге лежит gitignored `.env` с
`GENERATOR_API_KEY`, `GENERATOR_MODEL` и др.; `LLMClient.__init__` вызывает
`load_dotenv()`, поэтому значения из `.env` перебивают `monkeypatch.setenv`.
В чистом checkout/CI файла `.env` нет — baseline зелёный. Это дефект изоляции
тестов (тесты не очищают `GENERATOR_*`/`QC_*`), а не падение прод-кода.
Файл `.env` возвращён на место; в git он не попадает (`.gitignore:1`).

### K0.3 Статический анализ

```text
$ ruff check .
All checks passed!

$ bandit -r src run_pipeline.py app.py -ll -q
(пусто)   EXIT=0

$ python scripts/check_modularity.py
OK: all files <= 500 lines and functions <= 50 lines
```

### K0.4 История git (полный mirror-клон)

Клон: `/tmp/audit-history` (`git clone --mirror`, затем `core.bare false` +
`checkout`). Всего коммитов: `git rev-list --all --count` → **33**.

gitleaks:

```text
$ gitleaks detect --source . --log-opts="--all" --redact -v
gitleaks version 8.30.1
31 commits scanned.
scanned ~301853 bytes (301.85 KB) in 1.73s
no leaks found
```

(31, а не 33: gitleaks не сканирует merge/пустые коммиты; секретов не найдено.)

История `input/` и `demo/`:

```text
$ git log --all --oneline -- input demo
d47c9a1 PA-11: honest documentation, security and tech-debt docs, audit report
177e7cd chore: prepare repository for public showcase
0ae497d feat: init pipeline with ingestion, retrieval, and outline generation

Файлы за всю историю: demo/README.md, demo/expected/Final_Report.docx,
demo/expected/QC_Report.md, demo/input/{company_brief,market_data,methodology}.md,
input/{company_brief,market_data,methodology}.md
```

Проверка секретов в истории:

```text
$ git log --all --oneline -- '*.docx' '.env*' '*.pem'
82db8c9 Architectural fix: separate LLM for generation (GPT-4o-mini) and QC (GLM-4)
3a5fab9 Switch LLM provider from DeepSeek to OpenRouter (GPT-4o-mini)
1c023d5 Switch LLM provider from DeepSeek to OpenRouter (GPT-4o-mini)
177e7cd chore: prepare repository for public showcase
0ae497d feat: init pipeline with ingestion, retrieval, and outline generation

$ git log --all --name-only --pretty=format: | sort -u | grep -iE '\.env|\.pem|\.key|\.docx'
.env.example
demo/expected/Final_Report.docx
```

Словесные находки:

- Реальных `.env`, `.pem`, `.key`, приватных ключей и боевых токенов в истории
  никогда не было; единственный env-файл — `.env.example` с плейсхолдерами.
- `input/*.md` (EdTech Юго-Восточная Азия) не содержит текста задания
  работодателя, реальных ФИО, e-mail, телефонов, ссылок на закрытые источники.
  Названия компаний (`GoToClass`, `EduVn`, `PhilLearn`, `ThaiEdTech`) и цифры
  выглядят вымышленными/обобщёнными, но, в отличие от `demo/input/*.md`,
  **не помечены как synthetic** — происхождение цифр не задокументировано.
- `demo/input/*.md` явно помечены «Fully synthetic», реальных данных нет.
- `demo/expected/QC_Report.md` содержит только синтетические метрики
  (Northwind Traders, 62→72 и т.п.).

### K0.5 Упоминания DeepSeek

```text
$ grep -rn "DEEPSEEK" . --exclude-dir=.git
./docs/project-structure.md:13: ... smoke_llm.py ... needs DEEPSEEK_API_KEY ...
./docs/reports/portfolio-audit-report.md:177: ... (DEEPSEEK_API_KEY снят ...)
./docs/reports/portfolio-audit-report.md:185: ValueError: DEEPSEEK_API_KEY is not set ...

$ grep -rniE "deepseek" . --exclude-dir=.git
./docs/project-structure.md:13
./docs/limitations.md:10   ("The pipeline uses DeepSeek only")
./docs/reports/portfolio-audit-report.md:177,185
./SECURITY.md:8,26
./ARCHITECTURE.md:95
```

Итог: в коде и `.env.example` DeepSeek уже нет (там OpenRouter:
`GENERATOR_MODEL=openai/gpt-4o-mini`, `QC_MODEL=z-ai/glm-5.3-flash`);
упоминания остались только в документации, включая исторический audit-отчёт.
`ARCHITECTURE.md:95`, `docs/limitations.md:10`, `SECURITY.md:8/26`,
`docs/project-structure.md:13` — устаревшие утверждения, требуют правки в
K2/K7.

### K0.6 Скриншоты

| Файл | Что изображено | Цифры | Личные данные / ключи / пути |
| --- | --- | --- | --- |
| `docs/qc-report.png` | Титул «AI Quality Control Report — Demo Run», Northwind Traders (synthetic) | Draft 62/100, Final 72/100, +10; issues 13 (9/3/1) → 12 (5/7/0); 5 HIGH остаются | нет |
| `docs/final-document.png` | Первая страница DOCX «Market Entry Report: Specialty Coffee in Germany and Austria» | AI Quality Score 72/100; дата 2026-10-08 | нет |
| `docs/pipeline.png` | Схема пайплайна, шаги 1–7 (Ingestion → Retrieval → Outline → Section → QC → Revision → Final QC → Assembly) | — | только относительные пути `input/*.md`, `project_state/chunks.json`, `output/` |
| `docs/assets/demo_main_screen.png` | Streamlit UI: загрузка 3 файлов, «Document generated successfully!» | Draft 62 → Final 74, +12, resolved 12/12, 2 HIGH остаются | нет (имена файлов общие) |
| `docs/assets/demo_qc_report.png` | QC-отчёт в UI | Draft 62/100 (12 issues: 6/5/1) → Final 74/100 (11: 2/8/1), +12, resolved 12/12, sections improved 5 | нет |

Находки по скриншотам:

- Ключей, ФИО, e-mail, абсолютных путей и токенов не видно.
- `demo_qc_report.png` содержит цифры из **EdTech**-датасета
  (Индонезия $3.1B, Вьетнам $2.0B, Филиппины $1.7B, Таиланд $1.4B,
  Малайзия $1.2B, «AI улучшает результаты на 30%»), а не из coffee-демо.
  Скриншот не соответствует заявленному demo-датасету.
- Расхождение метрик: `docs/qc-report.png` — 62→72; `demo_main_screen.png` и
  `demo_qc_report.png` — 62→74 (+12), при этом `demo/expected/QC_Report.md` —
  62→72. Нужно согласовать в K2/K7.

### K0.7 Документы

| Файл | Проверено | Находки |
| --- | --- | --- |
| `ARCHITECTURE.md` | целиком | Устарело: «minimal OpenAI-compatible client for DeepSeek» и «There is no provider abstraction» — фактически OpenRouter + отдельные generator/QC конфиги. Секретов/реальных данных нет. |
| `docs/project-structure.md` | целиком | `smoke_llm.py` описан как требующий `DEEPSEEK_API_KEY` (фактически `LLM_API_KEY`/`GENERATOR_API_KEY`); в дереве перечислены 8 тестов из 16. |
| `demo/input/*.md` | целиком | Явно synthetic, реальных имён/контактов/закрытых цифр нет. Секретов нет. |
| `input/company_brief.md`, `input/market_data.md`, `input/methodology.md` | целиком | Секретов, ФИО, контактов, ссылок на закрытые источники нет. Но нет пометки «synthetic»: конкретные цифры и названия компаний выглядят вымышленными, однако их происхождение не задокументировано — риск ложного впечатления о реальных данных. |

### K0.8 Вывод

- Baseline в чистом checkout зелёный: **125 passed, coverage 91.21%**,
  порог 80% пройден. ruff/bandit/modularity — зелёные.
- При наличии локального `.env` baseline красный (5 failed) из-за
  `load_dotenv()` и загрязнения env — **отдельный дефект изоляции тестов**,
  не блокер публикации, но требует задачи в K2/K7.
- Секретов в истории нет (gitleaks: `no leaks found`).
- Главные содержательные находки: устаревшие DeepSeek-упоминания,
  несогласованные метрики/скриншоты, EdTech-цифры в coffee-демо-скриншоте,
  отсутствие пометки synthetic у `input/*.md`.
- Push не выполнялся: по условию K0 результат сначала показывается владельцу.
