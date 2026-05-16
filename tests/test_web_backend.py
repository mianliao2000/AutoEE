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
        self.assertIn("executionPlan", payload)
        self.assertIn("partsCatalog", payload)
        self.assertIn("pcbAutomationPlan", payload)
        self.assertIn("testWorkflow", payload)
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
        self.assertTrue(payload["executionPlan"]["items"])
        self.assertTrue(payload["partsCatalog"]["items"])
        first_part = payload["partsCatalog"]["items"][0]
        self.assertIn("digikey", first_part["supplierLinks"])
        self.assertIn("mouser", first_part["supplierLinks"])
        pcb_steps = {step["step"] for step in payload["pcbAutomationPlan"]["automationSteps"]}
        self.assertIn("Gerber Export", pcb_steps)
        self.assertIn("JLCPCB Handoff", pcb_steps)
        self.assertTrue(payload["testWorkflow"]["available"])
        self.assertGreaterEqual(len(payload["testWorkflow"]["cards"]), 4)
        self.assertIn("flashLog", payload["testWorkflow"]["codes"])
        self.assertGreaterEqual(len(payload["testWorkflow"]["data"]["efficiencyPoints"]), 4)
        self.assertIn("revisionActions", payload["testWorkflow"]["report"])
        test_stage_status = {stage["id"]: stage["status"] for stage in payload["stages"]}
        self.assertEqual(test_stage_status["embedded_coding_download"], "complete")
        self.assertEqual(test_stage_status["closed_loop_tuning"], "complete")
        self.assertEqual(test_stage_status["efficiency_logging"], "complete")
        self.assertEqual(test_stage_status["test_report"], "complete")
        self.assertTrue(payload["fakeCapabilityNotices"])
        badge_text = " ".join(f"{badge['sourceType']} {badge['signoffStatus']}" for badge in payload["evidenceBadges"])
        self.assertIn("not signoff", badge_text)
        self.assertIn("mock", badge_text)

        rerun_response = client.post("/api/run-demo")
        self.assertEqual(rerun_response.status_code, 200)
        rerun_state = rerun_response.json()["state"]
        self.assertTrue(rerun_response.json()["started"])
        self.assertEqual(rerun_state["workflowStatus"], "running")
        self.assertFalse(rerun_state["rawState"]["deterministic_results"])
        self.assertEqual(rerun_state["stages"][0]["status"], "waiting")

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

    def test_profile_fake_demo_runs_only_selected_request(self):
        client = self.make_client()
        rf_payload = {
            "requestId": "rf_embedded_sensor",
            "requestText": "Design a 2.4 GHz BLE wireless temperature sensor node powered by a coin cell.",
            "domain": "rf_communication",
            "productType": "wireless_sensor_node",
            "workflowSteps": [
                {"id": "rf_requirements", "title": "RF Requirements", "phase": "Design"},
                {"id": "rf_ic_selection", "title": "RF IC", "phase": "Design"},
                {"id": "link_budget", "title": "Link Budget", "phase": "Design"},
                {"id": "wireless_compliance", "title": "Compliance", "phase": "Test"},
            ],
        }
        response = client.post("/api/run-demo", json=rf_payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["state"]["demoMode"], "profile_fake")
        self.assertEqual(response.json()["state"]["activeDemoRequestId"], "rf_embedded_sensor")

        deadline = time.monotonic() + 10.0
        payload = {}
        while time.monotonic() < deadline:
            payload = client.get("/api/state").json()
            if payload["workflowStatus"] == "complete":
                break
            time.sleep(0.05)

        self.assertEqual(payload["workflowStatus"], "complete")
        self.assertEqual(payload["demoMode"], "profile_fake")
        self.assertEqual(payload["activeDemoDomain"], "rf_communication")
        self.assertFalse(payload["rawState"]["deterministic_results"])
        stage_status = {stage["id"]: stage["status"] for stage in payload["activeDemoStages"]}
        self.assertEqual(stage_status["rf_requirements"], "complete")
        self.assertEqual(stage_status["link_budget"], "complete")
        self.assertTrue(all(stage["status"] == "waiting" for stage in payload["stages"]))

    def test_switching_from_power_to_profile_demo_clears_power_results(self):
        client = self.make_client()
        response = client.post("/api/run-demo")
        self.assertEqual(response.status_code, 200)

        deadline = time.monotonic() + 10.0
        power_payload = {}
        while time.monotonic() < deadline:
            power_payload = client.get("/api/state").json()
            if power_payload["workflowStatus"] == "complete":
                break
            time.sleep(0.05)
        self.assertTrue(power_payload["rawState"]["deterministic_results"])

        response = client.post("/api/run-demo", json={
            "requestId": "analog_sensor",
            "requestText": "Design a low-noise thermocouple measurement front-end with ADC output.",
            "domain": "analog_sensor",
            "productType": "thermocouple_measurement_front_end",
            "workflowSteps": [
                {"id": "signal_chain", "title": "Signal Chain", "phase": "Design"},
                {"id": "noise_budget", "title": "Noise Budget", "phase": "Design"},
                {"id": "calibration", "title": "Calibration", "phase": "Test"},
            ],
        })
        self.assertEqual(response.status_code, 200)
        analog_state = response.json()["state"]
        self.assertEqual(analog_state["demoMode"], "profile_fake")
        self.assertFalse(analog_state["rawState"]["deterministic_results"])
        self.assertEqual(analog_state["stages"][0]["status"], "waiting")


if __name__ == "__main__":
    unittest.main()
