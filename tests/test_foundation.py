import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from autoee_demo.core import AutoEEAgent, DesignState, ProjectSpec, check_approval, load_project_spec_yaml, save_project_spec_yaml
from autoee_demo.model_backend import MemorySecretStore, ModelBackendSettings, ModelManager
from evals.metrics import evaluate_design_state


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def mock_manager():
    return ModelManager(ModelBackendSettings(default_provider="mock"), MemorySecretStore())


class FoundationTests(unittest.TestCase):
    def test_project_spec_yaml_round_trip(self):
        spec = ProjectSpec()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "current_spec.yaml"
            save_project_spec_yaml(spec, path)
            loaded = load_project_spec_yaml(path)
        self.assertEqual(loaded.output_voltage_v, spec.output_voltage_v)
        self.assertEqual(loaded.output_current_a, spec.output_current_a)
        self.assertEqual(loaded.input_voltage_max_v, spec.input_voltage_max_v)

    def test_repo_current_spec_loads(self):
        spec = load_project_spec_yaml(ROOT / "specs" / "current_spec.yaml")
        self.assertEqual(spec.output_voltage_v, 5.0)
        self.assertEqual(spec.output_current_a, 3.0)

    def test_evaluator_empty_state_is_missing_not_pass(self):
        summary = evaluate_design_state(DesignState())
        self.assertEqual(summary.overall_status, "missing")
        self.assertIn("selected_bom.high_side_mosfet", summary.missing_data)

    def test_evaluator_partial_state_is_missing(self):
        agent = AutoEEAgent(model_manager=mock_manager())
        agent.run_skill("spec_analyzer")
        agent.run_skill("component_search")
        summary = evaluate_design_state(agent.state)
        self.assertEqual(summary.overall_status, "missing")
        self.assertEqual(summary.categories["bom_status"], "partial")
        self.assertEqual(summary.categories["loss_thermal_status"], "missing")

    def test_evaluator_full_offline_workflow_is_partial(self):
        agent = AutoEEAgent(model_manager=mock_manager())
        with tempfile.TemporaryDirectory() as tmp:
            agent.run_all(output_dir=Path(tmp))
        summary = agent.state.deterministic_results["validation"]["evaluation_summary"]
        self.assertEqual(summary["overall_status"], "partial")
        self.assertEqual(summary["categories"]["manufacturing_status"], "blocked_requires_approval")
        self.assertTrue(summary["missing_data"])

    def test_safety_gate_blocks_real_risky_action_without_approval(self):
        blocked = check_approval("firmware_flash", approve=False, dry_run=False)
        self.assertFalse(blocked.allowed)
        dry_run = check_approval("firmware_flash", approve=False, dry_run=True)
        self.assertTrue(dry_run.allowed)
        approved = check_approval("firmware_flash", approve=True, dry_run=False)
        self.assertTrue(approved.allowed)

    def test_cli_evaluator_writes_reports(self):
        state = DesignState()
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "design_state.json"
            out_dir = Path(tmp) / "reports"
            state.save_json(state_path)
            result = subprocess.run(
                [sys.executable, str(ROOT / "evals" / "evaluate_design.py"), "--state", str(state_path), "--out", str(out_dir)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertIn("overall_status=missing", result.stdout)
            parsed = json.loads((out_dir / "eval_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(parsed["overall_status"], "missing")
            self.assertTrue((out_dir / "eval_summary.md").exists())

    def test_gui_has_design_console_widgets(self):
        from PyQt5 import QtWidgets
        from autoee_demo.ui.main import MainWindow

        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
        window = MainWindow()
        try:
            self.assertIsNotNone(window.design_overview)
            self.assertIsNotNone(window.design_rationale)
            self.assertIsNotNone(window.switching_canvas)
            self.assertIsNotNone(window.loss_canvas)
            self.assertIsNotNone(window.tile_ripple)
            self.assertIsNotNone(window.tile_missing)
            self.assertIn("Design Overview", [window.plot_tabs.tabText(i) for i in range(window.plot_tabs.count())])
            self.assertIn("Design Rationale", [window.plot_tabs.tabText(i) for i in range(window.plot_tabs.count())])
            self.assertIn("Loss + Thermal", [window.plot_tabs.tabText(i) for i in range(window.plot_tabs.count())])
        finally:
            window.close()

    def test_design_rationale_contains_quick_check_formulas(self):
        from PyQt5 import QtWidgets
        from autoee_demo.ui.main import MainWindow

        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
        window = MainWindow()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                window.agent.run_all(output_dir=Path(tmp) / "run")
                window.render_state()
            text = window.design_rationale.toPlainText()
            self.assertIn("Design Rationale Quick Check", text)
            self.assertIn("D = Vout / Vin", text)
            self.assertIn("Pcond = IL,rms^2", text)
            self.assertIn("Tj = Ta + Pcomponent", text)
            self.assertIn("synthetic", text.lower())
            self.assertIn("Missing data count", text)
        finally:
            window.close()

    def test_gui_has_investor_demo_mode_and_snapshot(self):
        from PyQt5 import QtWidgets
        from autoee_demo.ui.main import MainWindow

        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
        window = MainWindow()
        try:
            tabs = [window.workspace_tabs.tabText(i) for i in range(window.workspace_tabs.count())]
            self.assertIn("Investor Demo", tabs)
            self.assertIn("Engineering Console", tabs)
            self.assertEqual(window.workspace_tabs.currentWidget(), window.investor_demo)
            self.assertEqual(window.investor_demo.btn_run_demo.text(), "Run 3-Min Demo")
            self.assertIn("Design Package", window.investor_demo.package_view.toPlainText())
            with tempfile.TemporaryDirectory() as tmp:
                window.agent.run_all(output_dir=Path(tmp) / "run")
                window.render_state()
                snapshot = window.export_investor_snapshot(Path(tmp) / "snapshots")
                text = snapshot.read_text(encoding="utf-8")
            self.assertIn("AutoEE Investor Snapshot", text)
            self.assertIn("mock", text.lower())
            self.assertIn("synthetic", text.lower())
            self.assertIn("not signoff", text.lower())
            self.assertNotIn("signoff-ready evidence", text.lower().replace("not signoff-ready evidence", ""))
            window.on_reset_demo()
            self.assertFalse(window.agent.state.deterministic_results)
            self.assertEqual(window.agent.state.spec.output_voltage_v, 5.0)
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
