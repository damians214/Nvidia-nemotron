
"""Local HTTP API for the Veridex dashboard."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from agent.orchestrator import Pipeline
from backend.config import Settings
from backend.contracts import BackendError, Policies, Run
from backend.exports import export_run
from backend.store import Store


HOST = "127.0.0.1"
PORT = 8767
WEB_ROOT = (Path(__file__).resolve().parent.parent / "frontend" / "web").resolve()

settings = Settings.from_env()
store = Store(settings.data_root)
jobs = {}
jobs_lock = threading.Lock()


def summarize(record):
    candidate = record.candidates[-1] if record.candidates else None

    return {
        "run_id": record.id,
        "mode": record.mode,
        "state": record.state,
        "outcome": record.outcome,
        "error": record.error,
        "findings": [
            finding.model_dump()
            for finding in record.baseline_scan.findings
        ],
        "events": [event.model_dump() for event in record.events],
        "candidate": {
            "status": candidate.status,
            "original_text": candidate.original_text,
            "patched_text": candidate.patched_text,
            "diff": candidate.diff,
            "checks": [check.model_dump() for check in candidate.checks],
            "review": (
                candidate.review.model_dump()
                if candidate.review else None
            ),
        } if candidate else None,
    }


def run_pipeline(run_id):
    with jobs_lock:
        record = jobs[run_id]["record"]

    try:
        pipeline = Pipeline(settings)
        pipeline.scan(record)

        if (
            record.state == "AWAITING_SELECTION"
            and record.baseline_scan.findings
        ):
            finding_id = record.baseline_scan.findings[0].id
            pipeline.investigate(record, finding_id)

        export_run(record, store)

    except Exception:
        # Do not expose exception details or provider credentials.
        record.state = "FAILED"
        record.error = "Pipeline execution failed. Check local server logs."

        try:
            export_run(record, store)
        except Exception:
            pass

    finally:
        with jobs_lock:
            jobs[run_id]["running"] = False


class Handler(BaseHTTPRequestHandler):
    def send_json(self, payload, status=200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlsplit(self.path).path

        if path == "/api/health":
            return self.send_json({
                "status": "ok",
                "scanner_configured": settings.scanner.is_file(),
                "model_configured": bool(settings.api_key),
                "repositories": list(settings.repositories),
            })

        if path.startswith("/api/runs/"):
            run_id = path.removeprefix("/api/runs/")

            with jobs_lock:
                job = jobs.get(run_id)

            if job:
                with jobs_lock:
                    result = summarize(job["record"])
                    result["running"] = job["running"]
                return self.send_json(result)

            try:
                record = store.load(run_id)
            except (BackendError, ValueError, OSError, KeyError):
                return self.send_json({"error": "Run not found"}, 404)

            result = summarize(record)
            result["running"] = False
            return self.send_json(result)

        if path == "/":
            path = "/index.html"

        # Only serve files inside the approved dashboard directory.
        target = (WEB_ROOT / path.lstrip("/")).resolve()

        if not target.is_relative_to(WEB_ROOT) or not target.is_file():
            self.send_error(404)
            return

        types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".png": "image/png",
            ".svg": "image/svg+xml",
        }

        data = target.read_bytes()
        self.send_response(200)
        self.send_header(
            "Content-Type",
            types.get(target.suffix, "application/octet-stream"),
        )
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        path = urlsplit(self.path).path

        if path != "/api/run":
            return self.send_json({"error": "Unknown endpoint"}, 404)

        try:
            length = int(self.headers.get("Content-Length", "0"))

            if not 0 <= length <= 4096:
                return self.send_json({"error": "Invalid request size"}, 400)

            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError("Expected JSON object")

            repository = body.get("repository", "sample")

            if repository not in settings.repositories:
                return self.send_json(
                    {"error": "Repository is not approved"},
                    400,
                )

            max_lines = body.get("max_changed_lines", 24)
            policies = Policies(max_changed_lines=max_lines)

            record = Run(
                repository_id=repository,
                policies=policies,
            )

            with jobs_lock:
                jobs[record.id] = {
                    "record": record,
                    "running": True,
                }

            worker = threading.Thread(
                target=run_pipeline,
                args=(record.id,),
                daemon=True,
            )
            worker.start()

            return self.send_json({
                "run_id": record.id,
                "state": record.state,
                "running": True,
            }, 202)

        except (ValueError, TypeError, json.JSONDecodeError):
            return self.send_json({"error": "Invalid request"}, 400)


if __name__ == "__main__":
    print(f"Veridex dashboard: http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
