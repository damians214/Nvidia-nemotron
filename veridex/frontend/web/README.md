# Veridex — Reference-Matched UI Prototype

A standalone responsive frontend modeled on the team's slide-5 dashboard reference. Branded for **VERIDEX** with the shield logo and slogan **Don't just fix it. Verify it.**

## Run in VS Code

Open this folder in VS Code and run:

```bash
python3 -m http.server 8503
```

Open **http://localhost:8503**. No Python packages or Streamlit installation are required.

## Controls

- **Display:** Light / Dark / System in the top-right dropdown.
- **Density:** Comfortable / Compact in the top-right dropdown.
- **Navigation:** Overview, Investigations, Vulnerabilities, Agent Control, Analytics, Reports.
- **Run Investigation / Step Mode:** advances an illustrative investigation timeline.
- **Code preview:** Diff / Original / Patched tabs.
- **Quick actions:** export sample patch and sample evidence JSON. Create PR is disabled pending a backend.

## Important

This is a **frontend-only design prototype**, not the existing Streamlit application or your teammate's backend. Sample metrics, findings, activity, and patches are illustrative. No NVIDIA Nemotron or OpenGrep calls are made, and no patch is security-verified. To integrate real data, wire the UI to your backend separately; do not overwrite the existing repository.
