# Security

Internal overview prepared with AI assistance. Not an independent audit.

## Threat model

The pipeline is designed for local, single-user use. The main asset is the
DeepSeek API key, which is read from a project-local `.env` file or from the
environment. The process runs on the operator's machine and writes reports to
`output/` and intermediate state to `project_state/`.

## What is protected

- The API key is not stored in the repository; only the placeholder in
  `.env.example` is tracked.
- `.env` and its variants are listed in `.gitignore`.
- Uploaded file names are reduced to their base name, so path traversal such as
  `../x.md` becomes `x.md`; only `.md` and `.txt` files are accepted.
- The cleanup helper deletes only `.md`/`.txt` files and refuses to run on the
  project root or inside `demo/`.

## What is not protected

- The Streamlit UI has no authentication, no user accounts, and no access
  control.
- Document text and source fragments are sent to the external DeepSeek API.
  There is no on-premise mode and no local model.
- There is no encryption at rest for `project_state/` or `output/`.
- There is no rate limiting or audit log.

## Demo status

The Streamlit demo is an HTTP development server without TLS. It is not
intended for real, personal, or confidential data (DEMO-04). Treat it as a
local demonstration only.

## Scan results

Both scans were run on the current branch before the PA-11 commit.

- **bandit** — files only: `bandit -r src run_pipeline.py app.py -ll -q`.
  Result: exit 0, no findings at High or Medium severity, empty output.
- **gitleaks** — full git history: `gitleaks detect --source . --log-opts="--all" --redact`.
  Result: exit 0, 23 commits scanned, no leaks found.

No automated dependency audit is part of this document.

## Reporting

This is a portfolio project, not a maintained service. If you notice a security
issue, contact the repository owner directly.
