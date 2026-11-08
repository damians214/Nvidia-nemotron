# Veridex

An evidence-driven Python security investigation app for the HackUTD NVIDIA Nemotron challenge. The hackathon backend implements real OpenGrep scanning, restricted native Nemotron tool calling, candidate verification, a separate advisory reviewer pass, and patch/Evidence Passport export. It keeps original repositories unchanged.

**Validation status:** real scanner integration and recorded-model end-to-end tests are available. A live Nemotron acceptance run requires your NVIDIA key and a tool-capable model; missing credentials never trigger simulated fallback.

## Start locally

Use Python 3.12 (the tested runtime):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python scripts/install_opengrep.py
cp .env.example .env
# Edit .env: set NVIDIA_API_KEY and NVIDIA_MODEL. Do not commit it.
python -m backend.cli doctor
streamlit run frontend/app.py
```

Open http://127.0.0.1:8501. The default **Live investigation** workspace can scan the bundled sample without NVIDIA credentials. Select a finding and use **Investigate with Nemotron** after configuring the provider. Relevant source excerpts are sent to the configured NVIDIA endpoint.

The separate **Design demo** route retains the original v12 visual prototype and labels its findings, activity, candidates and review as simulated.

## Implemented hackathon workflow

- Operator-approved repository IDs; private snapshots of bounded UTF-8 Python files.
- Rejection of traversal, symlinks, special files, unsupported files and oversized input.
- Pinned OpenGrep v1.33.1, backend-owned SQL construction rules, full accepted-file coverage checks, raw scanner evidence and timeouts.
- Native model tool calls validated against strict schemas; no shell or target-code execution tool.
- One selected file per candidate; original hash checks; two bounded attempts with rejected history retained.
- AST syntax, no-new-import, small-diff, suppression and structural integrity checks; fresh-copy rescans and conservative finding comparison.
- Separate reviewer context with structured verdicts and validated source/check references.
- SQLite run/event persistence and complete or partial Evidence Passports with source excerpts, versions, hashes, actual statuses and limitations.
- Thin Streamlit developer/executive views, plus headless CLI and actual patch downloads.

No scanner result or model verdict proves security or functional correctness. The application never executes repository code/tests, applies changes to originals, or publishes PRs. Human review is required.

## Headless commands

```bash
python -m backend.cli scan --repository sample
python -m backend.cli investigate <run_id> --finding <finding_id>
python -m backend.cli run --repository sample
python -m backend.cli export <run_id>
```

Run IDs and export paths are printed as JSON. Scanner/model failures return nonzero exit codes while preserving partial evidence. Use the two-stage scan/investigate commands to choose a specific finding.

## Validate

```bash
# Deterministic tests and Streamlit interactions. External suites are explicitly skipped.
python -m unittest discover -s tests -p 'test_*.py' -v

# Real pinned scanner, with clearly labeled recorded model responses.
VERIDEX_REAL_SCANNER=1 python -m unittest tests.test_scanner_integration -v
python scripts/smoke_recorded.py

# Actual NVIDIA API and OpenGrep; requires credentials, consumes provider quota.
VERIDEX_LIVE_SMOKE=1 python -m unittest tests.test_live_smoke -v
```

The recorded smoke intentionally proposes an unsafe SQL candidate before a parameterized candidate. Its exports say `RECORDED_TEST`; they never claim Nemotron ran.

## Scope and documentation

The hackathon milestone ends at M5 with a thin UI. M6 background workers, Step/cancel/reset/revision controls and M7 operational hardening are later milestones. The UI captures policies at scan creation; start a new scan to change them. Simultaneously generated patch alternatives, YAML policy uploads and repository/PR integrations are P2.

- [Setup and demo runbook](docs/hackathon-runbook.md)
- [Backend implementation plan](docs/backend-implementation-plan.md)

This is an independent student project, not an official NVIDIA product. The retained design demo uses NVIDIA-inspired green, the Verified Shield asset, optional motion, theme controls, Patch Arena and demonstration evidence exports.
