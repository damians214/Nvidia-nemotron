"""Thin Streamlit consumer of the real backend. Design demo is a separate route."""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from agent.orchestrator import Pipeline
from backend.config import Settings
from backend.contracts import BackendError, Policies, Run
from backend.exports import passport, patch_bytes
from backend.store import Store


def render_live():
    st.title("Veridex")
    st.caption("Detect → Investigate → Verify → Human review")
    st.info("Live backend · OpenGrep and Nemotron results are recorded from actual calls. Original repository files are never patched.")
    try:
        settings = Settings.from_env()
        store = Store(settings.data_root)
    except (ValueError, OSError):
        st.error("Invalid application configuration. Check .env and the approved repository registry.")
        return
    with st.sidebar:
        st.subheader("Investigation")
        repository = st.selectbox("Approved repository", list(settings.repositories), key="live_repo")
        st.caption("Investigation sends relevant source excerpts to the configured NVIDIA endpoint. Use repositories approved for that purpose.")
        no_imports = st.checkbox("No new imports", value=True, key="live_no_imports")
        minimal = st.checkbox("Enforce small diff", value=True, key="live_minimal")
        scope = st.select_slider("Maximum added and removed lines", options=[12, 24, 48, 96, 192], value=24, key="live_scope")
        st.caption("Policies are captured when a scan is created. Start a new scan to change them.")
        st.write("Scanner:", "Installed" if settings.scanner.is_file() else "Not installed")
        st.write("Nemotron:", "Configured" if settings.api_key and settings.model else "Needs credentials/model")
        if st.button("New scan", type="primary", key="live_scan"):
            record = Run(repository_id=repository, policies=Policies(no_new_imports=no_imports, minimal_diff=minimal, max_changed_lines=scope))
            st.session_state.live_run_id = record.id
            with st.spinner("Creating an isolated snapshot and running OpenGrep…"):
                Pipeline(settings).scan(record)
        if st.button("Clear current view", key="live_clear"):
            st.session_state.pop("live_run_id", None)
        st.caption("Hackathon controls: scan, select, investigate and export. Background jobs, cancellation and step mode are planned for M6.")
    run_id = st.session_state.get("live_run_id")
    if not run_id:
        st.write("Choose the bundled SQL injection sample or an operator-approved repository, then select **New scan**.")
        if not settings.scanner.is_file():
            st.code("python scripts/install_opengrep.py", language="bash")
        if not settings.api_key or not settings.model:
            st.warning("Add NVIDIA_API_KEY and NVIDIA_MODEL to veridex/.env to enable live investigation. Scanning works without them.")
        return
    try:
        record = store.load(run_id)
    except KeyError:
        st.error("Run is no longer available in local storage.")
        return
    developer, executive, architecture = st.tabs(["Developer workspace", "Executive overview", "Architecture"])
    with developer:
        st.write("Run", record.id)
        st.write("Mode", record.mode)
        if record.mode != "LIVE":
            st.warning("RECORDED_TEST run: model responses are fixtures, not live Nemotron output.")
        st.write("State", record.state)
        if record.error:
            st.error(record.error)
        if record.outcome == "NO_FINDINGS":
            st.warning("No findings detected by the bundled narrow SQL rules. No model review or patch was produced.")
        findings = record.baseline_scan.findings
        if findings:
            choices = {f.id: f"{f.severity} · {f.file}:{f.line} · {f.message}" for f in findings}
            selected = st.selectbox("Finding to investigate", list(choices), format_func=choices.get, key="live_finding_" + run_id)
            if st.button("Investigate with Nemotron", disabled=record.state != "AWAITING_SELECTION", key="live_investigate"):
                with st.spinner("Running bounded model tools, independent checks and a separate review…"):
                    Pipeline(settings).investigate(record, selected)
                st.rerun()
            st.dataframe([f.model_dump() for f in findings], hide_index=True, width="stretch")
        if record.candidates:
            candidate = record.candidates[-1]
            st.subheader("Proposed patch")
            st.write("Candidate status", candidate.status)
            st.code(candidate.diff, language="diff")
            st.dataframe([{"Check": c.name, "Status": c.status, "Details": c.details} for c in candidate.checks], hide_index=True, width="stretch")
            st.write("Scan comparison", candidate.comparison)
            if candidate.review:
                st.subheader("Independent advisory review")
                st.json(candidate.review.model_dump())
            st.caption("AST parsing checks syntax only. Scanner clearance and reviewer acceptance do not guarantee security or behavior.")
        st.subheader("Recorded activity")
        st.dataframe([{"Time": e.timestamp, "Stage": e.stage, "Action": e.action, "Status": e.status, "Detail": e.detail}
                      for e in record.events], hide_index=True, width="stretch")
        st.download_button("Download Evidence Passport", json.dumps(passport(record), indent=2),
                           file_name=f"veridex-{record.id}.json", mime="application/json", key="live_passport")
        patch = patch_bytes(record)
        if patch is not None:
            st.download_button("Download proposed patch", patch, file_name=f"veridex-{record.id}.patch",
                               mime="text/x-patch", key="live_patch")
        st.caption("Exports contain source code. Share only with authorized reviewers.")
    with executive:
        a, b, c = st.columns(3)
        a.metric("Baseline findings", len(record.baseline_scan.findings))
        b.metric("Candidates", len(record.candidates))
        c.metric("Ready for human review", sum(x.status == "READY" for x in record.candidates))
        if findings:
            from collections import Counter
            counts = Counter(f.severity for f in findings)
            st.bar_chart([{"Severity": k, "Findings": v} for k, v in counts.items()], x="Severity", y="Findings")
        st.write("Original accepted source unchanged:", "Measured unchanged" if record.original_unchanged else "Unknown / not measured")
        st.write("Model requests:", record.model_requests, "· Tool calls:", record.tool_calls)
        st.write("Outcome:", record.outcome or record.state)
    with architecture:
        st.write("Streamlit → Python state machine → restricted Nemotron tools → isolated snapshot → OpenGrep and AST/policy checks → separate reviewer → evidence exports.")
        st.write("The hackathon backend supports UTF-8 Python, one selected file per attempt and two bounded attempts. Repository code and tests are not executed. No original files are overwritten.")
        st.caption("Independent student project; not an official NVIDIA product.")
