"""Opt-in tests against the actual pinned OpenGrep binary, no live model calls."""
from __future__ import annotations

import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from agent.orchestrator import Pipeline
from backend.config import APP_ROOT, Settings
from backend.contracts import Run
from backend.exports import passport
from scanner.opengrep_runner import OpenGrep
from tests.recorded_provider import RecordedNemotron, SAFE, UNSAFE


@unittest.skipUnless(os.environ.get("VERIDEX_REAL_SCANNER") == "1", "Set VERIDEX_REAL_SCANNER=1 to run the real pinned scanner suite")
class RealScannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.repo = cls.root / "repository"
        cls.repo.mkdir()
        (cls.repo / "app.py").write_bytes((APP_ROOT / "samples/sql_injection/app.py").read_bytes())
        cls.settings = replace(Settings.from_env(), data_root=cls.root / "data", repositories={"sample": cls.repo})

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def execute(self, candidates=None):
        run = Run(repository_id="sample", mode="RECORDED_TEST")
        pipeline = Pipeline(self.settings, provider=RecordedNemotron(candidates))
        pipeline.scan(run)
        self.assertEqual(run.state, "AWAITING_SELECTION", run.error)
        self.assertTrue(run.baseline_scan.executed)
        self.assertEqual(len(run.baseline_scan.findings), 1)
        pipeline.investigate(run, run.baseline_scan.findings[0].id)
        return run

    def test_real_scan_safe_patch_and_review_pipeline(self):
        run = self.execute()
        self.assertEqual(run.state, "READY_FOR_HUMAN_REVIEW", run.error)
        c = run.candidates[-1]
        self.assertTrue(c.rescan.executed)
        self.assertEqual(c.rescan.findings, [])
        from workspace.manager import digest
        self.assertEqual(run.baseline_scan.raw_hash, digest(run.baseline_scan.raw_json.encode()))
        self.assertEqual(c.rescan.raw_hash, digest(c.rescan.raw_json.encode()))
        self.assertIn("--no-rewrite-rule-ids", c.rescan.command)
        self.assertTrue(run.original_unchanged)
        self.assertEqual(passport(run)["mode"], "RECORDED_TEST")
        self.assertEqual(run.baseline_scan.findings[0].rule_id, "veridex.python.sql-string-construction")

    def test_real_scanner_rejects_formatted_sql_then_accepts_bound_parameters(self):
        run = self.execute([UNSAFE, SAFE])
        self.assertEqual(run.state, "READY_FOR_HUMAN_REVIEW", run.error)
        self.assertEqual([c.status for c in run.candidates], ["REJECTED", "READY"])
        self.assertEqual(run.candidates[0].comparison, "STILL_DETECTED")

    def test_suppression_and_deletion_never_reach_rescan_clearance(self):
        for candidate in (SAFE + "# nosemgrep\n", "pass\n"):
            with self.subTest(candidate=candidate[:20]):
                run = self.execute([candidate])
                self.assertEqual(run.state, "INCONCLUSIVE", run.error)
                self.assertFalse(any(c.status == "READY" for c in run.candidates))
                self.assertFalse(any(c.rescan.executed for c in run.candidates))

    def test_shifted_lines_still_detected(self):
        source = (self.repo / "app.py").read_text()
        run = self.execute(["\n\n" + source])
        self.assertEqual(run.state, "INCONCLUSIVE", run.error)
        self.assertEqual(run.candidates[0].comparison, "STILL_DETECTED")

    def test_added_match_blocks_acceptance(self):
        extra = SAFE + '\ndef other(conn, user):\n    return conn.execute("SELECT " + user)\n'
        run = self.execute([extra])
        self.assertEqual(run.state, "INCONCLUSIVE", run.error)
        self.assertFalse(any(c.status == "READY" for c in run.candidates))

    def test_empty_scan_is_actual_zero_findings(self):
        directory = self.root / "safe"
        directory.mkdir(exist_ok=True)
        (directory / "app.py").write_text(SAFE)
        from workspace.manager import digest
        scan = OpenGrep(self.settings).scan(directory, {"app.py": digest(SAFE.encode())})
        self.assertEqual(scan.status, "PASS", scan.errors)
        self.assertEqual(scan.findings, [])
        self.assertEqual(scan.scanned, ["app.py"])
