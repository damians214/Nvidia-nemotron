"""python -m backend.cli: headless hackathon workflow and diagnostics."""
from __future__ import annotations

import argparse
import json
import sys

from agent.orchestrator import Pipeline
from backend.config import Settings
from backend.contracts import BackendError, Policies, Run
from backend.exports import export_run
from backend.store import Store


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Veridex local static security investigator")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Report configuration without revealing credentials")
    scan = sub.add_parser("scan", help="Snapshot an approved repository and run OpenGrep")
    scan.add_argument("--repository", default="sample")
    investigate = sub.add_parser("investigate", help="Investigate a finding from a previous scan")
    investigate.add_argument("run_id")
    investigate.add_argument("--finding", help="Exact finding ID; defaults to the first finding")
    run = sub.add_parser("run", help="Scan then investigate the first finding with live Nemotron")
    run.add_argument("--repository", default="sample")
    run.add_argument("--max-changed-lines", type=int, default=24)
    export = sub.add_parser("export", help="Export existing real/partial run evidence")
    export.add_argument("run_id")
    args = parser.parse_args(argv)
    try:
        settings = Settings.from_env()
        store = Store(settings.data_root)
        if args.command == "doctor":
            print(json.dumps({"python": sys.version.split()[0], "scanner_exists": settings.scanner.is_file(),
                              "scanner_checksum_configured": bool(settings.scanner_sha256),
                              "provider_key_configured": bool(settings.api_key), "model": settings.model or "NOT CONFIGURED",
                              "repositories": list(settings.repositories), "data_root": str(settings.data_root)}, indent=2))
            return 0
        if args.command == "export":
            print(json.dumps(export_run(store.load(args.run_id), store), indent=2))
            return 0
        pipeline = Pipeline(settings)
        if args.command == "investigate":
            record = store.load(args.run_id)
        else:
            record = Run(repository_id=args.repository, policies=Policies(max_changed_lines=getattr(args, "max_changed_lines", 24)))
            pipeline.scan(record)
        if args.command in {"run", "investigate"} and record.state == "AWAITING_SELECTION":
            finding_id = getattr(args, "finding", None) or record.baseline_scan.findings[0].id
            pipeline.investigate(record, finding_id)
        paths = export_run(record, store)
        print(json.dumps({"run_id": record.id, "mode": record.mode, "state": record.state, "outcome": record.outcome,
                          "findings": [f.model_dump() for f in record.baseline_scan.findings],
                          "error": record.error, "exports": paths}, indent=2))
        return 0 if record.state in {"AWAITING_SELECTION", "READY_FOR_HUMAN_REVIEW"} else 1
    except (BackendError, ValueError, OSError, KeyError) as exc:
        print(f"Configuration or command error: {type(exc).__name__}. Check inputs and run doctor.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
