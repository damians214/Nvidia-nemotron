# Veridex hackathon runbook

The hackathon implementation covers the M0–M5 investigation path with a thin Streamlit interface. This runbook explains how to install it, demonstrate actual scanner evidence, configure live NVIDIA inference, and interpret results. Background job controls and enterprise deployment remain outside this milestone.

## Setup

Run commands from `veridex/` using Python 3.12. Create `.venv`, activate it, and install `requirements.lock`. The lock captures the versions tested during implementation; `requirements.txt` lists the direct dependencies. Install the scanner with `python scripts/install_opengrep.py`.

The installer downloads official OpenGrep v1.33.1 into `.tools/` for macOS ARM/Intel or Linux ARM/x86. It records the initial HTTPS download's SHA-256 in `.tools/toolchain.json`; this is an installation integrity pin, not publisher signature verification. The runner refuses a changed binary or unexpected version. The Veridex-authored rules in `scanner/rules/python-sql.yml` cover the sample's SQL concatenation/interpolation patterns, not all SQL vulnerabilities.

Copy `.env.example` to `.env` and set `NVIDIA_API_KEY` and the exact tool-capable `NVIDIA_MODEL` authorized for your account. `NVIDIA_BASE_URL` defaults to `https://integrate.api.nvidia.com/v1`. The client uses native Chat Completions tool calls and a separate JSON reviewer response. Validate both capabilities on your chosen endpoint; tool support is model-specific. See [NVIDIA's tool-calling documentation](https://docs.nvidia.com/nim/large-language-models/2.1.4/advanced-use-cases/tool-calling-and-mcp.html).

Only the application's `.env` is read, as literal values without shell execution. Environment variables take precedence. Do not put provider credentials in the target repository. Configuration errors and authentication failures stop the investigation; they never activate demo responses.

Run `python -m backend.cli doctor` to see scanner presence, pin presence, model ID and credential availability without revealing the key. Start `streamlit run frontend/app.py` and open `http://127.0.0.1:8501`. The committed Streamlit configuration binds to localhost and disables usage telemetry.

## Live demonstration

1. Leave application mode set to **Live investigation** and repository set to **sample**. The sample is deliberately vulnerable; the app will not execute it.
2. Set the no-new-import/small-diff policies and select **New scan**. Policies are captured for that run.
3. Inspect the real finding at `app.py`, the selected rule and severity, and the scan events. The original stays untouched.
4. Select **Investigate with Nemotron**. The model must request actual scoped file reads and submit complete replacement text with the observed original hash.
5. Inspect the candidate diff, syntax/policy outcomes, disposable-copy rescan, and separate reviewer verdict. Up to two candidate attempts are retained.
6. Download the proposed `.patch` and Evidence Passport JSON. These explicitly include source content; share them only with authorized reviewers.

A candidate is ready only when the independent gates pass and the separate reviewer returns ACCEPT with valid source/check references. Rejection, uncertainty, failed scans, invalid citations and exhausted budgets remain visible. No proposed patch is automatically applied to the original or published.

The current thin UI performs bounded work synchronously. It provides scan, finding selection, investigation and export. Use a new scan for another investigation or policy choice; **Clear current view** preserves stored evidence. Run/Step/cancel/reset/revision controls with background workers belong to M6. Avoid overlapping UI/CLI commands against the same run; distributed execution and command idempotency are outside this milestone.

## Command line demonstration

`python -m backend.cli scan --repository sample` prints the actual finding IDs, run ID and partial Passport path. Then use `python -m backend.cli investigate RUN_ID --finding FINDING_ID`. `python -m backend.cli run --repository sample` combines these stages and chooses the first finding. `python -m backend.cli export RUN_ID` recreates the current exports from persisted records.

For a credential-free integration rehearsal, run `python scripts/smoke_recorded.py`. This uses the real pinned scanner with deterministic recorded model protocol responses. It first proposes unsafe formatted SQL, preserves its rejection, then verifies a parameterized candidate. The result and exports are marked `RECORDED_TEST`. It is evidence for scanner/orchestration integration, not evidence for Nemotron accuracy or live connectivity.

The v12 **Design demo** remains available as a separately labeled simulated route. Its scripted findings, reviewer and animation are not acceptance evidence for the live pipeline.

## Approving another local repository

Set `VERIDEX_REPOSITORIES` in the application `.env` to a JSON object mapping an operator-selected ID to an absolute approved directory, for example `{"my-project":"/absolute/path/to/project"}`. The UI uses IDs, not unrestricted host paths. The bundled `sample` remains available. Use repositories whose relevant source may be sent to the configured provider.

Only UTF-8 `.py` files enter the snapshot. Other extensions, `.git`, dependency/build directories and common credential directories are excluded and recorded. Encountered symlinks and special files are rejected. Copy limits are 2,000 accepted files, 1 MiB per file, 50 MiB total, 32 path components and 8,000 encountered entries. Newline-terminated originals/candidates are required for portable patch export. Choose a small relevant Python sample if coverage or context limits are exceeded.

All original paths are read-only to backend operations. Snapshot reads use anchored no-follow file descriptors; candidates are written only to new disposable copies. Before/after accepted-source manifests measure preservation. Concurrent external source changes result in unknown preservation rather than an unsupported assertion that Veridex changed the repository.

## Evidence and privacy

SQLite stores run snapshots and their event history transactionally. The default private data directory is the platform's temporary directory under `veridex-local`; `doctor` prints the exact location. Set `VERIDEX_DATA_ROOT` to a private persistent directory outside every target repository if evidence must survive operating-system temporary-file cleanup.

Each run has an immutable baseline and separate candidate directories. Exports go under `artifacts/RUN_ID/`. Scanner JSON, source/patch hashes, excerpts, model request references, prompt versions, check statuses, advisory verdict, rejected attempts and limitations are included. Check states distinguish PASS, FAIL, NOT_RUN and INCONCLUSIVE. A scan's PASS status means execution and coverage completed; use its findings and comparison to assess what was detected.

Raw scanner JSON is preserved in scan records and hashed over its original bytes. Telemetry carries bounded sanitized action summaries rather than source/prompts or provider response bodies. Outbound model context is blocked on known secret patterns or the configured API key. This is best-effort detection, not a substitute for approving repository content. Patches preserve exact candidate bytes; they are never silently redacted into a different patch.

The `.patch` download has a metadata preamble plus unified diff hunks. Its SHA-256 covers the exact download; the separate diff hash covers hunks. The JSON contains both. Source-bearing data is private local state, not encrypted multi-user storage. No automatic expiry, backup service or deletion UI is included in M5. Stop the application before operator-managed archival/removal of its dedicated data root. Do not remove unrelated temporary files or active workspaces.

## Budgets and interpretation

The default run limits are two candidate attempts, eight total provider requests including transport retries/reviews, twelve tools, 64,000 cumulative token budget units, a 32,000-byte serialized context guard, and 2,000 output tokens per request. Provider calls have a 60-second timeout, scans a 120-second deadline, and each active scan/investigation phase a 10-minute deadline. First scanner version/cache initialization has a separate 60-second cap. Output capture is limited to 8 MiB. At most two transient transport retries use bounded backoff; authentication and malformed-response errors do not retry.

Provider token counts are recorded when supplied. Missing usage uses a conservative byte estimate marked `estimated`; interrupted transient requests reserve budget and are counted as usage unknown. Cost is always unknown in this milestone. Provider billing cannot be inferred from a local failure.

Finding comparison is intentionally conservative: any remaining same-rule match in the selected file prevents clearance, even if another duplicate is the remaining match. Additional rule/path match counts also block promotion. This avoids claiming clearance from moved lines or ambiguous duplicate identity. Integrity checks preserve function names/arity, existing conditional checks and call targets, but remain heuristics. AST parsing and static scans do not prove behavior preservation, and the target's code/test suite is never executed.

## Tests and acceptance

- Deterministic suite: `python -m unittest discover -s tests -p 'test_*.py' -v`.
- Real scanner suite: `VERIDEX_REAL_SCANNER=1 python -m unittest tests.test_scanner_integration -v`.
- Live acceptance: `VERIDEX_LIVE_SMOKE=1 python -m unittest tests.test_live_smoke -v` with credentials configured. This calls NVIDIA, uses quota and fails if the actual pipeline does not complete; it does not use recorded responses.

GitHub Actions runs the deterministic and pinned-scanner suites. An explicit workflow dispatch can opt into the live gate using repository secret `NVIDIA_API_KEY` and variable `NVIDIA_MODEL`. A skipped live test is not a live acceptance pass.

The tests cover traversal, symlinks/special files, limits, stale hashes, strict tool arguments, prompt-injection boundaries, syntax/import/scope/integrity policies, safe/unsafe SQL, suppression/deletion, new/moved findings, failed/malformed/partial scans, timeouts, output limits, provider failures/retries, citation validation, canceled/partial evidence, original preservation, actual patch applicability, and thin Streamlit interactions.

## Troubleshooting

If scanning fails, check the pin/version and reinstall the official binary if necessary. A nonzero exit, invalid JSON, timeout or incomplete accepted-file inventory remains inconclusive; do not interpret empty findings as clearance. A rejected unsupported encoding or large repository should be reduced to an approved relevant UTF-8 Python sample.

If inference fails, check key/model/endpoint/quota and native tool-calling support. The investigator will not interpret plain text as a tool invocation. The independent reviewer must support JSON output and valid evidence references. The Passport preserves available evidence so failure can be explained without rerunning the original scan.

If the process exits mid-investigation, its last persisted record may remain at an active stage. M5 does not automatically replay calls or recover background jobs; create a new run and use the old partial export for diagnosis. This avoids accidentally duplicating billed model requests. M6 provides job lifecycle recovery.
