"""Exercise real OpenGrep with labeled recorded model responses, never claim live AI."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.orchestrator import Pipeline
from backend.config import Settings
from backend.contracts import Run
from backend.exports import export_run
from tests.recorded_provider import RecordedNemotron, SAFE, UNSAFE


def main():
    settings = Settings.from_env()
    provider = RecordedNemotron([UNSAFE, SAFE])
    pipeline = Pipeline(settings, provider=provider)
    run = Run(repository_id="sample", mode="RECORDED_TEST")
    pipeline.scan(run)
    if run.state == "AWAITING_SELECTION":
        pipeline.investigate(run, run.baseline_scan.findings[0].id)
    exports = export_run(run, pipeline.store)
    print(json.dumps({"mode": run.mode, "scanner": "REAL OpenGrep", "model": "RECORDED fixture; Nemotron was not called",
                      "state": run.state, "run_id": run.id, "error": run.error,
                      "attempts": [{"status": c.status, "comparison": c.comparison} for c in run.candidates],
                      "original_unchanged": run.original_unchanged, "exports": exports}, indent=2))
    return 0 if run.state == "READY_FOR_HUMAN_REVIEW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
