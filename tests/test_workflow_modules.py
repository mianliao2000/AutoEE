import json
import tempfile
import unittest
from pathlib import Path

from autoee_demo.core import AutoEEAgent, DesignState, ProjectSpec
from autoee_demo.model_backend import MemorySecretStore, ModelBackendSettings, ModelManager


def mock_manager():
    return ModelManager(ModelBackendSettings(default_provider="mock"), MemorySecretStore())


class WorkflowModuleTests(unittest.TestCase):
    def test_full_agent_workflow_runs_offline(self):
        agent = AutoEEAgent(model_manager=mock_manager())
        with tempfile.TemporaryDirectory() as tmp:
            agent.run_all(output_dir=Path(tmp))
        state = agent.state
        self.assertEqual(state.workflow_status, "complete")
        for module_id in [
            "spec_analyzer",
            "component_search",
            "loss_thermal",
            "open_loop_sim",
            "emag_maxwell",
            "closed_loop_control",
            "library_pcb_mechanical",
            "embedded_coding_download",
            "closed_loop_tuning",
            "efficiency_logging",
            "test_report",
            "validation",
            "report_generator",
            "skill_memory",
        ]:
            self.assertIn(module_id, state.deterministic_results)
        self.assertIn("execution_plan", state.deterministic_results["spec_analyzer"])
        bom = state.deterministic_results["component_search"]["selected_bom"]
        high_side = bom["high_side_mosfet"]
        self.assertIn("supplier_links", high_side)
        self.assertIn("digikey", high_side["supplier_links"])
        self.assertIn("mouser", high_side["supplier_links"])
        self.assertIn("unit_price_usd", high_side)
        self.assertIn("stock_qty", high_side)
        self.assertIn("key_params", high_side)
        pcb_steps = state.deterministic_results["library_pcb_mechanical"]["automation_steps"]
        step_names = {step["step"] for step in pcb_steps}
        for expected in ["Schematic Generation", "Placement", "Routing", "Gerber Export", "JLCPCB Handoff"]:
            self.assertIn(expected, step_names)
        firmware = state.deterministic_results["embedded_coding_download"]
        self.assertEqual(firmware["realCapabilityStatus"], "not_connected")
        self.assertIn("flashLog", firmware)
        tuning = state.deterministic_results["closed_loop_tuning"]
        self.assertIn("parameterSweep", tuning)
        self.assertIn("selectedParameters", tuning)
        logged = state.deterministic_results["efficiency_logging"]
        self.assertGreaterEqual(len(logged["efficiencyPoints"]), 4)
        self.assertIn("summaryCards", logged)
        test_report = state.deterministic_results["test_report"]
        self.assertIn("reportSummary", test_report)
        self.assertIn("revisionActions", test_report)

    def test_default_buck_specs_are_market_demo_values(self):
        spec = ProjectSpec()
        self.assertEqual(spec.input_voltage_min_v, 9.0)
        self.assertEqual(spec.input_voltage_max_v, 36.0)
        self.assertEqual(spec.output_voltage_v, 5.0)
        self.assertEqual(spec.output_current_a, 3.0)

    def test_loss_model_meets_demo_target(self):
        agent = AutoEEAgent(model_manager=mock_manager())
        agent.run_skill("spec_analyzer")
        agent.run_skill("component_search")
        agent.run_skill("loss_thermal")
        loss = agent.state.deterministic_results["loss_thermal"]["loss_breakdown"]
        self.assertLessEqual(loss["total_loss_w"], agent.state.spec.max_total_loss_w)
        self.assertGreaterEqual(loss["efficiency_percent"], agent.state.spec.target_efficiency_percent)
        self.assertIn("hs_mosfet_conduction", loss["items_w"])
        self.assertIn("inductor_core_placeholder", loss["items_w"])

    def test_control_skill_exports_bode_plot_for_gui(self):
        agent = AutoEEAgent(model_manager=mock_manager())
        for module_id in ["spec_analyzer", "component_search", "loss_thermal", "open_loop_sim", "closed_loop_control"]:
            agent.run_skill(module_id)
        control = agent.state.deterministic_results["closed_loop_control"]
        bode = control["bode_plot"]
        self.assertGreater(len(bode["freq_hz"]), 20)
        self.assertEqual(len(bode["freq_hz"]), len(bode["mag_db"]))
        self.assertIn("phase_margin_deg", bode["metrics"])

    def test_open_loop_sim_exports_waveform_lab_schema(self):
        agent = AutoEEAgent(model_manager=mock_manager())
        for module_id in ["spec_analyzer", "component_search", "loss_thermal", "open_loop_sim"]:
            agent.run_skill(module_id)
        sim = agent.state.deterministic_results["open_loop_sim"]["simulation_result"]
        waves = sim["waveforms"]
        for key in ["time_us", "vout_v", "il_a", "switch_v", "load_current_a", "duty_command"]:
            self.assertIn(key, waves)
            self.assertEqual(len(waves[key]), sim["metrics"]["sample_count"])
        self.assertLess(waves["load_current_a"][0], waves["load_current_a"][-1])
        self.assertGreater(max(waves["il_a"]), agent.state.spec.output_current_a)
        self.assertGreater(max(waves["switch_v"]), agent.state.spec.input_voltage_nominal_v * 0.9)
        self.assertLess(min(waves["switch_v"]), 0.1)
        self.assertIn("limit_bands", sim)
        self.assertIn("events", sim)
        self.assertEqual(sim["metrics"]["signoff_status"], "not_signoff_synthetic")

    def test_report_exports_json_and_markdown(self):
        agent = AutoEEAgent(model_manager=mock_manager())
        with tempfile.TemporaryDirectory() as tmp:
            agent.run_all(output_dir=Path(tmp))
            report = agent.state.deterministic_results["report_generator"]
            report_path = Path(report["markdown_report"])
            state_path = Path(report["design_state"])
            self.assertTrue(report_path.exists())
            self.assertTrue(state_path.exists())
            self.assertIn("Human Signoff Checklist", report_path.read_text(encoding="utf-8"))
            self.assertIn("Evaluation", report_path.read_text(encoding="utf-8"))
            parsed = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(parsed["spec"]["output_voltage_v"], 5.0)

    def test_spec_edit_can_clear_downstream_results(self):
        state = DesignState()
        state.deterministic_results["spec_analyzer"] = {"x": 1}
        state.deterministic_results["loss_thermal"] = {"y": 2}
        state.clear_from(["spec_analyzer", "loss_thermal"])
        self.assertNotIn("spec_analyzer", state.deterministic_results)
        self.assertNotIn("loss_thermal", state.deterministic_results)


if __name__ == "__main__":
    unittest.main()
