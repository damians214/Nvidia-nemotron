"""Evidence exported from executed records, never recomputed as a success claim."""
from __future__ import annotations

import json

from backend.contracts import Check, Run
from backend.store import Store
from workspace.manager import digest

LIMITATIONS = [
    "Static checks and an advisory model review cannot establish security or functional correctness.",
    "Repository code, scripts and test suites were not executed.",
    "Only accepted UTF-8 Python files and the bundled narrow SQL construction rules were scanned.",
    "Original preservation measures accepted source bytes; concurrent external changes are reported as unknown.",
    "Structural and small-diff policies are heuristics; human review and developer testing are required.",
]


def patch_bytes(run: Run) -> bytes | None:
    if not run.candidates:
        return None
    c = run.candidates[-1]
    statuses = ", ".join(f"{check.name}={check.status}" for check in c.checks) or "NOT RUN"
    preamble = (f"From: Veridex <local@veridex.invalid>\nDate: {c.created_at}\n"
                f"Subject: [PATCH] Proposed fix for {c.relative_path}\n\n"
                f"Run: {run.id}\nMode: {run.mode}\nCandidate status: {c.status}\n"
                f"Checks: {statuses}\nReview: {c.review.verdict if c.review else 'NOT RUN'}\n"
                "Limitations: Static analysis only; not proven secure or functionally correct. Human review required.\n\n")
    return (preamble + c.diff).encode()


def passport(run: Run) -> dict:
    c = run.candidates[-1] if run.candidates else None
    syntax = next((x for x in c.checks if x.name == "Python syntax"), Check(name="Python syntax")) if c else Check(name="Python syntax")
    patch = patch_bytes(run)
    limitations = list(LIMITATIONS)
    if run.mode != "LIVE":
        limitations.insert(0, "RECORDED_TEST: model responses came from deterministic test fixtures, not live Nemotron.")
    if run.state != "READY_FOR_HUMAN_REVIEW":
        limitations.insert(0, "Investigation did not complete all readiness gates.")
    selected = next((f for f in run.baseline_scan.findings if f.id == run.finding_id), None)
    return {
        "schema_version": run.schema_version, "product": "Veridex", "mode": run.mode,
        "run_id": run.id, "created_at_utc": run.created_at, "updated_at_utc": run.updated_at,
        "execution_status": run.state, "outcome": run.outcome, "error": run.error,
        "finding": selected.model_dump() if selected else None,
        "source": {"path": c.relative_path if c else None, "original_unchanged": run.original_unchanged,
                   "original_excerpt": c.original_text if c else None,
                   "patched_excerpt": c.patched_text if c else None,
                   "manifest": run.manifest, "manifest_hash": digest(json.dumps(run.manifest, sort_keys=True).encode()),
                   "exclusions": run.exclusions},
        "model_id": run.model_id, "prompt_versions": {"investigator": "1", "reviewer": "1"},
        "tool_versions": {"opengrep": run.baseline_scan.tool_version},
        "baseline_scan": run.baseline_scan.model_dump(),
        "syntax_check": syntax.model_dump(),
        "opengrep_rescan": c.rescan.model_dump() if c else {"executed": False, "status": "NOT_RUN"},
        "scan_comparison": c.comparison if c else "NOT_RUN",
        "policy_checks": [x.model_dump() for x in c.checks if x.name != "Python syntax"] if c else [],
        "policies": run.policies.model_dump(),
        "adversarial_review": {**c.review.model_dump(), "model_id": run.model_id, "request_id": c.review_request_id,
                               "candidate_hash": c.candidate_hash} if c and c.review else {"executed": False, "status": "NOT_RUN"},
        "activity_events": [x.model_dump() for x in run.events],
        "tool_invocations": [x.model_dump() for x in run.tool_receipts],
        "attempts": [x.model_dump() for x in run.candidates],
        "patch": patch.decode() if patch else None,
        "patch_hash": digest(patch) if patch else None,
        "diff_hash": digest(c.diff.encode()) if c else None,
        "candidate_hash": c.candidate_hash if c else None,
        "usage": {"model_requests": run.model_requests, "tool_calls": run.tool_calls,
                  "input_tokens": run.input_tokens, "output_tokens": run.output_tokens,
                  "estimated": run.usage_estimated, "unknown_requests": run.usage_unknown_requests, "cost": None},
        "limitations": limitations,
    }


def export_run(run: Run, store: Store) -> dict[str, str]:
    files = {"passport": str(store.write_artifact(run.id, "passport.json", json.dumps(passport(run), indent=2).encode()))}
    patch = patch_bytes(run)
    if patch is not None:
        files["patch"] = str(store.write_artifact(run.id, "candidate.patch", patch))
    return files
