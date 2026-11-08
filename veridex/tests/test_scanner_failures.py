"""Trusted subprocess fixtures verify scanner failure boundaries."""
import os
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from backend.config import Settings
from backend.contracts import BackendError, Canceled
from scanner.opengrep_runner import OpenGrep
from workspace.manager import digest


class ScannerFailureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "app.py").write_text("x = 1\n")
        self.manifest = {"app.py": digest(b"x = 1\n")}

    def scanner(self, body, **kwargs):
        fixture = self.root / "scanner-fixture"
        fixture.write_text(f"#!{sys.executable}\nimport sys,time,json\nif '--version' in sys.argv:\n print('1.33.1'); sys.exit(0)\n" + body)
        fixture.chmod(0o700)
        return OpenGrep(Settings(data_root=self.root / "data", scanner=fixture,
                                 scanner_sha256=digest(fixture.read_bytes()), **kwargs))

    def test_timeout_is_inconclusive(self):
        result = self.scanner("time.sleep(10)\n", scan_timeout=0.2).scan(self.root, self.manifest)
        self.assertTrue(result.executed)
        self.assertEqual(result.status, "INCONCLUSIVE")

    def test_bad_exit_json_and_coverage_never_clean(self):
        for body in ("sys.exit(2)\n", "print('not json')\n", 'print(json.dumps({"results":[],"errors":[],"paths":{"scanned":[]}}))\n'):
            with self.subTest(body=body):
                result = self.scanner(body).scan(self.root, self.manifest)
                self.assertEqual(result.status, "INCONCLUSIVE")

    def test_output_limit_is_inconclusive(self):
        scan = self.scanner("print('x'*50000)\n", max_output_bytes=1000).scan(self.root, self.manifest)
        self.assertEqual(scan.status, "INCONCLUSIVE")

    def test_cancel_terminates_scanner(self):
        with self.assertRaises(Canceled):
            self.scanner("time.sleep(10)\n").scan(self.root, self.manifest, lambda: True)

    def test_checksum_mismatch_blocks_execution(self):
        runner = self.scanner("print('unused')\n")
        runner.settings = replace(runner.settings, scanner_sha256="bad")
        with self.assertRaises(BackendError):
            runner.scan(self.root, self.manifest)
