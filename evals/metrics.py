from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from autoee_demo.core.safety import check_approval
from autoee_demo.core.state import DesignState


VALID_STATUSES = {"pass", "partial", "missing", "not_started", "blocked_requires_approval"}


@dataclass
class EvaluationIssue:
    category: str
    status: str
    message: str
    severity: str = "medium"

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass
class EvaluationSummary:
    overall_status: str
    categories: Dict[str, str]
    missing_data: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    recommended_next_actions: List[str] = field(default_factory=list)
    issues: List[EvaluationIssue] = field(default_factory=list)
    source: str = "AutoEE_evaluator_v1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status,
            "categories": dict(self.categories),
            "missing_data": list(self.missing_data),
            "risks": list(self.risks),
            "recommended_next_actions": list(self.recommended_next_actions),
            "issues": [issue.to_dict() for issue in self.issues],
            "source": self.source,
        }


def _safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _add_issue(summary: EvaluationSummary, category: str, status: str, message: str, severity: str = "medium") -> None:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid evaluation status: {status}")
    summary.issues.append(EvaluationIssue(category, status, message, severity))


def _has_positive_number(value: Any) -> bool:
    try:
        return float(value) > 0.0
    except (TypeError, ValueError):
        return False


def evaluate_design_state(state: DesignState) -> EvaluationSummary:
    summary = EvaluationSummary(overall_status="partial", categories={})
    results = state.deterministic_results
    spec = state.spec

    required_spec = {
        "spec.input_voltage_min_v": spec.input_voltage_min_v,
        "spec.input_voltage_nominal_v": spec.input_voltage_nominal_v,
        "spec.input_voltage_max_v": spec.input_voltage_max_v,
        "spec.output_voltage_v": spec.output_voltage_v,
        "spec.output_current_a": spec.output_current_a,
        "spec.target_efficiency_percent": spec.target_efficiency_percent,
        "spec.ambient_temp_c": spec.ambient_temp_c,
    }
    missing_spec = [key for key, value in required_spec.items() if not _has_positive_number(value)]
    if missing_spec:
        summary.categories["spec_status"] = "missing"
        summary.missing_data.extend(missing_spec)
        _add_issue(summary, "spec", "missing", "Required numerical spec fields are missing.", "high")
    else:
        summary.categories["spec_status"] = "pass"

    component = _safe_dict(results.get("component_search"))
    bom = _safe_dict(component.get("selected_bom"))
    required_parts = ["high_side_mosfet", "low_side_mosfet", "inductor", "input_capacitor", "output_capacitor"]
    missing_parts = [part for part in required_parts if part not in bom]
    if missing_parts:
        summary.categories["bom_status"] = "missing"
        summary.missing_data.extend([f"selected_bom.{part}" for part in missing_parts])
        _add_issue(summary, "bom", "missing", "Selected BOM is incomplete or not generated.", "high")
    else:
        backend = str(component.get("backend") or "")
        is_demo_catalog = backend in {"mock_digikey", "fake_digikey_mouser"}
        summary.categories["bom_status"] = "partial" if is_demo_catalog else "pass"
        if is_demo_catalog:
            summary.risks.append("BOM uses mock DigiKey data and must be replaced with distributor/datasheet-backed parts.")
        for part_name in required_parts:
            part_dict = _safe_dict(bom.get(part_name))
            if not part_dict.get("datasheet_url"):
                summary.missing_data.append(f"selected_bom.{part_name}.datasheet_url")
            if "mock" in str(part_dict.get("source", "")).lower():
                summary.risks.append(f"{part_name} is sourced from mock catalog.")

    loss_result = _safe_dict(results.get("loss_thermal"))
    loss = _safe_dict(loss_result.get("loss_breakdown"))
    thermal = _safe_dict(loss_result.get("thermal_result"))
    loss_items = _safe_dict(loss.get("items_w"))
    required_losses = [
        "hs_mosfet_conduction",
        "ls_mosfet_conduction",
        "hs_switching_overlap",
        "inductor_dcr",
        "inductor_core_placeholder",
        "output_cap_esr",
        "input_cap_rms_esr",
    ]
    missing_losses = [key for key in required_losses if key not in loss_items]
    if not loss or missing_losses or not thermal:
        summary.categories["loss_thermal_status"] = "missing"
        summary.missing_data.extend([f"loss_breakdown.items_w.{key}" for key in missing_losses])
        if not thermal:
            summary.missing_data.append("thermal_result")
        _add_issue(summary, "loss_thermal", "missing", "Loss or thermal results are missing.", "high")
    else:
        status = "partial" if "inductor_core_placeholder" in loss_items else "pass"
        summary.categories["loss_thermal_status"] = status
        if status == "partial":
            summary.risks.append("Inductor core loss is placeholder/low-confidence and requires datasheet or magnetic simulation signoff.")
        if float(loss.get("total_loss_w", 0.0)) > spec.max_total_loss_w:
            summary.risks.append("Estimated total loss exceeds the spec target.")
        if float(loss.get("efficiency_percent", 0.0)) < spec.target_efficiency_percent:
            summary.risks.append("Estimated efficiency is below the spec target.")

    sim_result = _safe_dict(_safe_dict(results.get("open_loop_sim")).get("simulation_result"))
    if not sim_result:
        summary.categories["simulation_status"] = "missing"
        summary.missing_data.append("open_loop_sim.simulation_result")
        _add_issue(summary, "simulation", "missing", "Open-loop simulation result is missing.", "high")
    else:
        backend = str(sim_result.get("backend", ""))
        summary.categories["simulation_status"] = "partial" if backend == "synthetic" else "pass"
        if backend == "synthetic":
            summary.risks.append("Open-loop simulation is synthetic and is not a signoff simulation.")
            summary.missing_data.append("simulation/waveforms/open_loop_waveforms.csv")

    control_result = _safe_dict(results.get("closed_loop_control"))
    control = _safe_dict(control_result.get("control_result"))
    bode = _safe_dict(control_result.get("bode_plot"))
    if not control:
        summary.categories["control_status"] = "missing"
        summary.missing_data.append("closed_loop_control.control_result")
        _add_issue(summary, "control", "missing", "Closed-loop control result is missing.", "medium")
    else:
        summary.categories["control_status"] = "partial" if str(bode.get("source")) == "analytical_synthetic_loop_gain" else "pass"
        if summary.categories["control_status"] == "partial":
            summary.risks.append("Control/Bode result is analytical synthetic data, not PLECS/LTspice-verified loop gain.")

    library = _safe_dict(results.get("library_pcb_mechanical"))
    if not library:
        summary.categories["pcb_status"] = "not_started"
        summary.missing_data.extend(["pcb/schematic", "pcb/layout", "pcb/drc_reports", "pcb/erc_reports"])
    else:
        summary.categories["pcb_status"] = "partial"
        summary.risks.append("KiCad/FreeCAD/PCB output is a generation plan only; no verified ERC/DRC/layout exists.")
        summary.missing_data.extend(["pcb/schematic", "pcb/layout", "pcb/drc_reports", "pcb/erc_reports"])

    approval = check_approval("manufacturing_order", approve=False, dry_run=False)
    summary.categories["manufacturing_status"] = (
        "blocked_requires_approval" if not approval.allowed else "partial"
    )
    summary.risks.append(approval.reason)
    summary.missing_data.extend(["pcb/manufacturing/gerber", "pcb/manufacturing/drill", "pcb/manufacturing/cpl"])

    firmware = _safe_dict(results.get("embedded_coding_download"))
    if firmware:
        summary.categories["firmware_status"] = "partial"
        summary.risks.append("Firmware build, flashing, and target communication are demo data; no real prototype has been programmed.")
    else:
        firmware_approval = check_approval("firmware_flash", approve=False, dry_run=False)
        summary.categories["firmware_status"] = "blocked_requires_approval" if not firmware_approval.allowed else "not_started"
        summary.missing_data.extend(["firmware/generated", "firmware/build"])

    test_modules = {
        "embedded_coding_download": "firmware bring-up",
        "closed_loop_tuning": "closed-loop bench tuning",
        "efficiency_logging": "efficiency and thermal data logging",
        "test_report": "post-prototype test report",
    }
    completed_test_modules = [module_id for module_id in test_modules if module_id in results]
    if completed_test_modules:
        summary.categories["post_prototype_test_status"] = "partial"
        summary.risks.append("Post-prototype test results are fake lab data and are not measured signoff evidence.")
        missing_test_modules = [
            description
            for module_id, description in test_modules.items()
            if module_id not in results
        ]
        for description in missing_test_modules:
            summary.missing_data.append(f"post-prototype test module missing: {description}")
    else:
        summary.categories["post_prototype_test_status"] = "not_started"

    summary.categories["safety_status"] = "pass"

    if not summary.recommended_next_actions:
        if summary.categories.get("bom_status") != "pass":
            summary.recommended_next_actions.append("Replace mock BOM with distributor and datasheet-backed candidates.")
        if summary.categories.get("simulation_status") != "pass":
            summary.recommended_next_actions.append("Run PLECS/LTspice open-loop simulation and export waveform files.")
        if summary.categories.get("control_status") != "pass":
            summary.recommended_next_actions.append("Verify loop gain and transient response with simulation-backed control tuning.")
        if summary.categories.get("pcb_status") != "pass":
            summary.recommended_next_actions.append("Generate initial schematic/library artifacts and run ERC/DRC placeholders.")
        summary.recommended_next_actions.append("Keep manufacturing, firmware flashing, and lab tests in dry-run until explicitly approved.")

    status_values = set(summary.categories.values())
    if "missing" in status_values:
        summary.overall_status = "missing"
    elif "blocked_requires_approval" in status_values or "partial" in status_values or "not_started" in status_values:
        summary.overall_status = "partial"
    else:
        summary.overall_status = "pass"
    return summary


def write_evaluation_reports(summary: EvaluationSummary, out_dir: Path) -> Dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "eval_summary.json"
    md_path = out_dir / "eval_summary.md"
    payload = summary.to_dict()
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# AutoEE Evaluation Summary",
        "",
        f"Overall status: `{summary.overall_status}`",
        "",
        "## Categories",
        *[f"- {key}: `{value}`" for key, value in sorted(summary.categories.items())],
        "",
        "## Missing Data",
        *(f"- {item}" for item in summary.missing_data),
        "",
        "## Risks",
        *(f"- {item}" for item in summary.risks),
        "",
        "## Recommended Next Actions",
        *(f"- {item}" for item in summary.recommended_next_actions),
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"eval_summary_json": str(json_path), "eval_summary_markdown": str(md_path)}
