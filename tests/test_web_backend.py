from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from autoee_demo.web_app import WebDemoSession, create_app


class WebBackendTests(unittest.TestCase):
    def make_client(self):
        temp = tempfile.TemporaryDirectory()
        session = WebDemoSession(min_module_seconds=0.0, output_root=Path(temp.name) / "web_runs")
        client = TestClient(create_app(session))
        self.addCleanup(temp.cleanup)
        return client

    def test_state_endpoint_available_before_run(self):
        client = self.make_client()
        response = client.get("/api/state")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("prompt", payload)
        self.assertIn("spec", payload)
        self.assertEqual(payload["spec"]["input_voltage_min_v"], 9.0)
        self.assertIn("stages", payload)
        self.assertIn("designRationale", payload)
        self.assertGreaterEqual(len(payload["stages"]), 6)

    def test_update_spec_clears_old_results(self):
        client = self.make_client()
        response = client.post("/api/run-demo")
        self.assertEqual(response.status_code, 200)

        deadline = time.monotonic() + 10.0
        payload = {}
        while time.monotonic() < deadline:
            payload = client.get("/api/state").json()
            if payload["workflowStatus"] == "complete":
                break
            time.sleep(0.05)
        self.assertTrue(payload["rawState"]["deterministic_results"])

        spec = dict(payload["rawState"]["spec"])
        spec["output_current_a"] = 2.5
        update = client.post("/api/spec", json={"spec": spec})
        self.assertEqual(update.status_code, 200)
        updated_state = update.json()["state"]
        self.assertEqual(updated_state["rawState"]["spec"]["output_current_a"], 2.5)
        self.assertEqual(updated_state["workflowStatus"], "edited")
        self.assertFalse(updated_state["rawState"]["deterministic_results"])

    def test_update_spec_rejects_invalid_voltage_order(self):
        client = self.make_client()
        spec = dict(client.get("/api/state").json()["rawState"]["spec"])
        spec["input_voltage_min_v"] = 40.0
        response = client.post("/api/spec", json={"spec": spec})
        self.assertEqual(response.status_code, 400)

    def test_run_demo_reset_and_export_snapshot(self):
        client = self.make_client()
        response = client.post("/api/run-demo")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["started"])

        deadline = time.monotonic() + 10.0
        payload = {}
        while time.monotonic() < deadline:
            payload = client.get("/api/state").json()
            if payload["workflowStatus"] == "complete":
                break
            time.sleep(0.05)
        self.assertEqual(payload["workflowStatus"], "complete")
        self.assertIn("synthetic", payload["waveforms"]["sourceBadge"])
        self.assertTrue(payload["waveforms"]["controlBode"]["available"])
        self.assertIn("phase_margin_deg", payload["waveforms"]["controlBode"]["metrics"])
        badge_text = " ".join(f"{badge['sourceType']} {badge['signoffStatus']}" for badge in payload["evidenceBadges"])
        self.assertIn("not signoff", badge_text)
        self.assertIn("mock", badge_text)

        export = client.post("/api/export-snapshot").json()
        path = Path(export["path"])
        self.assertTrue(path.exists())
        text = path.read_text(encoding="utf-8").lower()
        self.assertIn("mock", text)
        self.assertIn("synthetic", text)
        self.assertIn("not-signoff", text)

        reset_payload = client.post("/api/reset").json()["state"]
        self.assertNotEqual(reset_payload["workflowStatus"], "complete")
        self.assertFalse(reset_payload["rawState"]["deterministic_results"])


if __name__ == "__main__":
    unittest.main()
