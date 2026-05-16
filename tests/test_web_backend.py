from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from autoee_demo.web_app import WebDemoSession, create_app


class WebBackendTests(unittest.TestCase):
    def make_client(self):
        temp = tempfile.TemporaryDirectory()
        db_path = Path(temp.name) / "data" / "projects.sqlite3"
        env_patch = patch.dict("os.environ", {"AUTOEE_PROJECT_DB": str(db_path)}, clear=False)
        env_patch.start()
        session = WebDemoSession(min_module_seconds=0.0, output_root=Path(temp.name) / "web_runs")
        client = TestClient(create_app(session))
        self.addCleanup(env_patch.stop)
        self.addCleanup(temp.cleanup)
        self.addCleanup(client.close)
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

    def test_run_demo_reset(self):
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

        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            rerun_payload = client.get("/api/state").json()
            if not rerun_payload["running"]:
                break
            time.sleep(0.05)

        reset_payload = client.post("/api/reset").json()["state"]
        self.assertNotEqual(reset_payload["workflowStatus"], "complete")
        self.assertFalse(reset_payload["rawState"]["deterministic_results"])

    def test_web_export_snapshot_endpoint_removed(self):
        client = self.make_client()
        self.assertIn(client.post("/api/export-snapshot").status_code, {404, 405})

    def test_run_skill_generates_analysis_and_simulation_artifacts(self):
        client = self.make_client()
        analysis = client.post("/api/run-skill", json={"skillId": "power.buck_analysis"})
        self.assertEqual(analysis.status_code, 200)
        analysis_payload = analysis.json()
        self.assertTrue(analysis_payload["ok"])
        state = analysis_payload["state"]
        self.assertTrue(state["analysisSummary"]["available"])
        self.assertIn("equations", state["analysisSummary"])
        self.assertGreaterEqual(len(state["analysisSummary"]["plots"]), 4)
        plot_url = state["analysisSummary"]["plots"][0]["url"]
        self.assertEqual(client.get(plot_url).status_code, 200)

        simulation = client.post("/api/run-skill", json={"skillId": "power.buck_simulation"})
        self.assertEqual(simulation.status_code, 200)
        sim_state = simulation.json()["state"]
        self.assertTrue(sim_state["simulationArtifacts"]["available"])
        self.assertIn("circuitModel", sim_state["simulationArtifacts"])
        self.assertGreaterEqual(len(sim_state["simulationArtifacts"]["plots"]), 3)
        self.assertIn(sim_state["simulationArtifacts"]["adapter"]["usedAdapter"], {"ngspice", "mock_adapter"})

    def test_copilot_chat_uses_configured_model_backend(self):
        with patch.dict("os.environ", {"AUTOEE_LLM_PROVIDER": "mock"}, clear=False):
            client = self.make_client()
        response = client.post("/api/copilot-chat", json={
            "requestText": "Design a buck converter.",
            "messages": [{"from": "user", "body": "What should I check next?"}],
        })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["message"]["provider"], "mock")
        self.assertIn("What should I check next?", payload["message"]["body"])

    def test_project_api_create_import_open_and_delete(self):
        client = self.make_client()
        project_payload = {
            "title": "Bench Supply Controller",
            "projectRequest": "Design a small controller board with connectors and LEDs.",
            "domainId": "general_pcb",
            "productType": "controller_board",
            "workflowSteps": [
                {"id": "requirement", "status": "ready"},
                {"id": "pcb", "status": "pending"},
            ],
        }
        create_response = client.post("/api/projects", json=project_payload)
        self.assertEqual(create_response.status_code, 200)
        project = create_response.json()["project"]
        self.assertEqual(project["sourceType"], "diy")
        self.assertEqual(project["title"], "Bench Supply Controller")
        self.assertEqual(project["moduleStatus"]["requirement"], "ready")
        self.assertEqual(project["progressPercent"], 0)

        list_response = client.get("/api/projects")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json()["projects"]), 1)

        open_response = client.post(f"/api/projects/{project['id']}/open")
        self.assertEqual(open_response.status_code, 200)
        self.assertEqual(open_response.json()["state"]["activeProjectId"], project["id"])

        import_response = client.post("/api/projects/import-demo", json={
            "title": "15W USB-C Buck Charger",
            "projectRequest": "Design a 15W USB-C buck charger from 9-36V input to 5V / 3A output.",
            "domainId": "power_energy",
            "productType": "DC/DC Buck Converter",
            "sourceDemoId": "power_buck_charger",
            "requirementPlan": {"status": "draft"},
        })
        self.assertEqual(import_response.status_code, 200)
        imported = import_response.json()["project"]
        self.assertEqual(imported["sourceType"], "demo")
        self.assertEqual(imported["sourceDemoId"], "power_buck_charger")

        delete_response = client.delete(f"/api/projects/{project['id']}")
        self.assertEqual(delete_response.status_code, 200)
        ids = {item["id"] for item in client.get("/api/projects").json()["projects"]}
        self.assertNotIn(project["id"], ids)
        self.assertIn(imported["id"], ids)

    def test_project_copilot_creates_and_applies_proposal(self):
        with patch.dict("os.environ", {"AUTOEE_LLM_PROVIDER": "mock"}, clear=False):
            client = self.make_client()
        project = client.post("/api/projects", json={
            "title": "Revision Project",
            "projectRequest": "Design a 15W USB-C buck charger.",
            "domainId": "power_energy",
            "productType": "DC/DC Buck Converter",
            "requirementPlan": {"status": "approved"},
            "workflowSteps": [
                {"id": "requirement", "status": "verified"},
                {"id": "analysis", "status": "ready"},
            ],
        }).json()["project"]

        chat_response = client.post(f"/api/projects/{project['id']}/copilot-chat", json={
            "task": {"id": project["copilotTasks"][0]["id"], "title": "Start Project"},
            "messages": [{"role": "user", "content": "Revise the requirement plan to reduce cost."}],
        })
        self.assertEqual(chat_response.status_code, 200)
        chat_payload = chat_response.json()
        self.assertTrue(chat_payload["proposal"])
        proposal_id = chat_payload["proposal"]["id"]

        apply_response = client.post(f"/api/projects/{project['id']}/proposals/{proposal_id}/apply")
        self.assertEqual(apply_response.status_code, 200)
        applied = apply_response.json()["project"]
        self.assertEqual(applied["requirementPlan"]["status"], "needs_review")
        self.assertEqual(applied["moduleStatus"]["analysis"], "outdated")
        self.assertEqual(applied["proposals"][0]["status"], "applied")

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
