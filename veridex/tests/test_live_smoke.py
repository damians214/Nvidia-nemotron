"""Explicit live acceptance gate. Never falls back to recorded model responses."""
import os
import unittest

from agent.orchestrator import Pipeline
from backend.config import Settings
from backend.contracts import Run
from backend.exports import export_run


@unittest.skipUnless(os.environ.get("VERIDEX_LIVE_SMOKE") == "1", "Live smoke not run; set credentials and VERIDEX_LIVE_SMOKE=1")
class LiveSmokeTests(unittest.TestCase):
    def test_live_nemotron_and_opengrep(self):
        settings = Settings.from_env()
        settings.validate_provider()
        pipeline = Pipeline(settings)
        run = Run(repository_id="sample")
        pipeline.scan(run)
        self.assertEqual(run.state, "AWAITING_SELECTION", run.error)
        pipeline.investigate(run, run.baseline_scan.findings[0].id)
        export_run(run, pipeline.store)
        self.assertEqual(run.mode, "LIVE")
        self.assertEqual(run.state, "READY_FOR_HUMAN_REVIEW", run.error)
        self.assertTrue(run.original_unchanged)
        self.assertGreater(run.tool_calls, 0)
        self.assertTrue(any(e.action == "Tool completed" and e.detail == "read_file" for e in run.events))
        self.assertTrue(run.candidates[-1].rescan.executed)
        self.assertIsNotNone(run.candidates[-1].review)
