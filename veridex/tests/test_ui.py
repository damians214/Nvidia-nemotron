"""Streamlit interaction checks use trusted local scanner fixtures."""
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from agent.orchestrator import Pipeline
from backend.config import APP_ROOT, Settings
from backend.contracts import Run
from tests.recorded_provider import RecordedNemotron
from tests.test_backend import FixtureScanner


class UITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = Settings(data_root=Path(self.temp.name) / "data")

    def app(self):
        return AppTest.from_file(str(APP_ROOT / "frontend/app.py"), default_timeout=60)

    def test_live_default_and_real_scan_command_wiring(self):
        with patch("frontend.live.Settings.from_env", return_value=self.settings), patch("frontend.live.Pipeline", side_effect=lambda settings: Pipeline(settings, scanner=FixtureScanner())):
            app = self.app().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.radio(key="application_mode").value, "Live investigation")
            app.button(key="live_scan").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(any("AWAITING_SELECTION" in m.value for m in app.markdown))
            app.button(key="live_investigate").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(any("Configure NVIDIA" in e.value for e in app.error))
            app.button(key="live_clear").click().run()
            self.assertFalse(app.exception)
            self.assertNotIn("live_run_id", app.session_state)

    def test_completed_record_renders_patch_checks_and_review(self):
        pipeline = Pipeline(self.settings, provider=RecordedNemotron(), scanner=FixtureScanner())
        record = Run(repository_id="sample", mode="RECORDED_TEST")
        pipeline.scan(record)
        pipeline.investigate(record, record.baseline_scan.findings[0].id)
        self.assertEqual(record.state, "READY_FOR_HUMAN_REVIEW", record.error)
        with patch("frontend.live.Settings.from_env", return_value=self.settings):
            app = self.app()
            app.session_state["live_run_id"] = record.id
            app.run()
            self.assertFalse(app.exception)
            self.assertTrue(any("RECORDED_TEST" in e.value for e in app.warning))
            self.assertTrue(any("SELECT * FROM users" in c.value for c in app.code))
            self.assertGreaterEqual(len(app.dataframe), 3)

    def test_design_demo_stays_explicitly_simulated(self):
        with patch("frontend.live.Settings.from_env", return_value=self.settings):
            app = self.app().run()
            app.radio(key="application_mode").set_value("Design demo").run()
            self.assertFalse(app.exception)
            self.assertTrue(any("SIMULATED" in m.value or "simulated" in m.value for m in app.markdown))
