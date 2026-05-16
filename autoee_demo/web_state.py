from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from autoee_demo.core.state import DesignState


INVESTOR_DEMO_PROMPT = "Design a vehicle/industrial 9-36V to 5V/3A USB-C buck charger."


def fmt_num(value: Any, suffix: str = "", digits: int = 2) -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(number) >= 10000 or (abs(number) < 0.001 and number != 0):
        text = f"{number:.2e}"
    elif abs(number) >= 1000:
        text = f"{number:.0f}"
    else:
        text = f"{number:.{digits}f}"
    return f"{text}{suffix}"


def fmt_hz(value: Any) -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(number) >= 1e6:
        return f"{number / 1e6:.2f} MHz"
    if abs(number) >= 1e3:
        return f"{number / 1e3:.2f} kHz"
    return f"{number:.0f} Hz"


def safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


HUMAN_LABELS = {
    "input_voltage_min_v": "minimum input voltage",
    "input_voltage_nominal_v": "nominal input voltage",
    "input_voltage_max_v": "maximum input voltage",
    "output_voltage_v": "output voltage",
    "output_current_a": "output current",
    "target_efficiency_percent": "target efficiency",
    "ambient_temp_c": "ambient temperature",
    "high_side_mosfet": "high-side MOSFET",
    "low_side_mosfet": "low-side MOSFET",
    "inductor": "inductor",
    "input_capacitor": "input capacitor",
    "output_capacitor": "output capacitor",
    "hs_mosfet_conduction": "high-side MOSFET conduction-loss estimate",
    "ls_mosfet_conduction": "low-side MOSFET conduction-loss estimate",
    "hs_switching_overlap": "high-side MOSFET switching-loss estimate",
    "inductor_dcr": "inductor copper-loss estimate",
    "inductor_core_placeholder": "inductor core-loss estimate",
    "output_cap_esr": "output capacitor ESR-loss estimate",
    "input_cap_rms_esr": "input capacitor RMS-loss estimate",
}


MISSING_DATA_MESSAGES = {
    "thermal_result": "Thermal result is missing, so component temperature risk has not been checked.",
    "open_loop_sim.simulation_result": "Open-loop simulation result is missing, so waveform behavior has not been reviewed.",
    "simulation/waveforms/open_loop_waveforms.csv": "Exported waveform data file is missing, so simulation traces cannot be independently reviewed.",
    "closed_loop_control.control_result": "Closed-loop control result is missing, so stability and compensation have not been reviewed.",
    "pcb/schematic": "Schematic file is missing.",
    "pcb/layout": "PCB layout file is missing.",
    "pcb/drc_reports": "PCB design-rule check report is missing.",
    "pcb/erc_reports": "Schematic electrical-rule check report is missing.",
    "pcb/manufacturing/gerber": "Gerber manufacturing files are missing.",
    "pcb/manufacturing/drill": "PCB drill files are missing.",
    "pcb/manufacturing/cpl": "Component placement file is missing.",
    "firmware/generated": "Generated firmware source is missing.",
    "firmware/build": "Compiled firmware build is missing.",
}


def _human_label(value: str) -> str:
    return HUMAN_LABELS.get(value, value.replace("_", " "))


def humanize_missing_data(item: Any) -> str:
    text = str(item)
    if text in MISSING_DATA_MESSAGES:
        return MISSING_DATA_MESSAGES[text]
    if text.startswith("spec."):
        return f"The {_human_label(text.split('.', 1)[1])} is not defined in the design specification."
    if text.startswith("selected_bom.") and text.endswith(".datasheet_url"):
        part = text.split(".")[1]
        return f"The {_human_label(part)} datasheet link is missing, so the selected part cannot be verified."
    if text.startswith("selected_bom."):
        part = text.split(".", 1)[1]
        return f"The {_human_label(part)} has not been selected in the bill of materials."
    if text.startswith("loss_breakdown.items_w."):
        loss_key = text.rsplit(".", 1)[1]
        return f"The {_human_label(loss_key)} is missing from the loss model."
    return text.replace("_", " ").replace("/", " / ").replace(".", " - ")


def humanize_risk(item: Any) -> str:
    text = str(item)
    if text.endswith(" is sourced from mock catalog."):
        part = text.replace(" is sourced from mock catalog.", "")
        return f"The {_human_label(part)} currently comes from a mock catalog and must be replaced with a verified supplier or datasheet-backed part."
    if text == "Blocked: risky hardware action requires --approve or HARDWARE_AGENT_APPROVAL=YES.":
        return "Real hardware actions are blocked until a human explicitly approves manufacturing, firmware flashing, or lab execution."
    return text


def _float_or_none(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def temp_tone(value: Any) -> str:
    temp = _float_or_none(value)
    if temp is None:
        return "unknown"
    if temp < 85.0:
        return "cool"
    if temp < 105.0:
        return "warm"
    if temp < 125.0:
        return "hot"
    return "critical"


def pass_fail_tone(passed: Optional[bool]) -> str:
    if passed is None:
        return "unknown"
    return "pass" if passed else "warn"


def _downsample(values: Iterable[Any], max_points: int = 900) -> List[Any]:
    values_list = list(values)
    if len(values_list) <= max_points:
        return values_list
    step = max(1, math.ceil(len(values_list) / max_points))
    return values_list[::step]


@dataclass(frozen=True)
class DemoStage:
    id: str
    title: str
    plain_english: str
    module_ids: List[str]
    generated_artifact: str
    evidence_level: str


DEMO_STAGES = [
    DemoStage(
        id="understand_specs",
        title="Understand Specs",
        plain_english="Translate a product ask into voltage, ripple, transient, efficiency, and thermal targets.",
        module_ids=["spec_analyzer"],
        generated_artifact="Constraint matrix",
        evidence_level="deterministic estimate",
    ),
    DemoStage(
        id="select_parts",
        title="Select Parts",
        plain_english="Pick a first power stage: MOSFETs, inductor, input caps, and output caps.",
        module_ids=["component_search"],
        generated_artifact="Initial BOM",
        evidence_level="mock catalog",
    ),
    DemoStage(
        id="loss_thermal",
        title="Estimate Loss And Heat",
        plain_english="Predict where watts turn into heat and whether components are approaching thermal limits.",
        module_ids=["loss_thermal"],
        generated_artifact="Loss and thermal model",
        evidence_level="first-order estimate",
    ),
    DemoStage(
        id="waveforms",
        title="Simulate Waveforms",
        plain_english="Show whether 5V stays stable while the load steps from light load to full power.",
        module_ids=["open_loop_sim"],
        generated_artifact="Vout, IL, switch node, and load-step waveforms",
        evidence_level="synthetic simulation",
    ),
    DemoStage(
        id="em_readiness",
        title="Prepare EM Check",
        plain_english="Create the handoff for magnetics, EMI, hot-loop, and Maxwell-style validation.",
        module_ids=["emag_maxwell"],
        generated_artifact="EM and magnetics job spec",
        evidence_level="placeholder checklist",
    ),
    DemoStage(
        id="control",
        title="Design Control",
        plain_english="Create a first closed-loop compensator seed and stability estimate.",
        module_ids=["closed_loop_control"],
        generated_artifact="Bode summary and control seed",
        evidence_level="analytical estimate",
    ),
    DemoStage(
        id="package",
        title="Build Package",
        plain_english="Assemble PCB/3D plan, risk evaluation, report, and reusable design memory.",
        module_ids=["library_pcb_mechanical", "validation", "report_generator", "skill_memory"],
        generated_artifact="Reviewable design package draft",
        evidence_level="needs signoff",
    ),
    DemoStage(
        id="embedded_coding_download",
        title="Codes",
        plain_english="Build demo firmware, flash the returned prototype, and record firmware identity and bring-up logs.",
        module_ids=["embedded_coding_download"],
        generated_artifact="Firmware image and flash transcript",
        evidence_level="fake lab workflow",
    ),
    DemoStage(
        id="closed_loop_tuning",
        title="Tuning",
        plain_english="Run a fake bench tuning sweep that turns the analytical control seed into selected register settings.",
        module_ids=["closed_loop_tuning"],
        generated_artifact="Closed-loop tuning sweep",
        evidence_level="fake lab workflow",
    ),
    DemoStage(
        id="efficiency_logging",
        title="Data",
        plain_english="Log fake efficiency, ripple, thermal, and instrument metadata across the operating points.",
        module_ids=["efficiency_logging"],
        generated_artifact="Efficiency and thermal data log",
        evidence_level="fake lab workflow",
    ),
    DemoStage(
        id="test_report",
        title="Report",
        plain_english="Generate a fake post-prototype report with evidence, pass/fail status, and Rev B actions.",
        module_ids=["test_report"],
        generated_artifact="Post-prototype test report",
        evidence_level="fake lab workflow",
    ),
]


INVESTOR_NARRATION = {
    "spec_analyzer": "I converted the product ask into engineering constraints: voltage range, ripple, transient, efficiency, and thermal targets.",
    "component_search": "I selected a first-pass power stage from a mock distributor catalog and kept the source label visible.",
    "loss_thermal": "I estimated where power becomes heat and translated it into component temperature risk.",
    "open_loop_sim": "I generated buck waveforms so viewers can see 5V regulation, inductor current, and load-step behavior.",
    "emag_maxwell": "I created the EM and magnetics handoff so a real Maxwell or EMI workflow can attach cleanly later.",
    "closed_loop_control": "I produced a first control seed and Bode stability view instead of leaving compensation as a manual step.",
    "library_pcb_mechanical": "I prepared the KiCad, PCB, and 3D generation plan while marking real library output as future signoff work.",
    "embedded_coding_download": "I generated fake firmware, flash, and bring-up evidence so the post-prototype workflow is visible in the demo.",
    "closed_loop_tuning": "I ran a fake bench tuning sweep that shows how measured load-step response would close the loop.",
    "efficiency_logging": "I created fake efficiency, ripple, and thermal logs to show the future automated test-data pipeline.",
    "test_report": "I assembled a fake post-prototype report with evidence links, pass/fail checks, and next-board actions.",
    "validation": "I evaluated the run honestly: what is complete, what is mock, what is synthetic, and what still needs proof.",
    "report_generator": "I exported the design state and report package so the run becomes a reviewable engineering artifact.",
    "skill_memory": "I saved reusable workflow memory so future designs can start from this experience.",
}


def module_status(module_id: str, state: DesignState, presentation_status: Optional[Dict[str, str]] = None) -> str:
    if presentation_status and presentation_status.get(module_id):
        return str(presentation_status[module_id])
    if module_id in state.deterministic_results:
        return "complete"
    return str(state.module_status.get(module_id) or "waiting")


def stage_status(stage: DemoStage, state: DesignState, presentation_status: Optional[Dict[str, str]] = None) -> str:
    statuses = [module_status(module_id, state, presentation_status) for module_id in stage.module_ids]
    if any(status == "running" for status in statuses):
        return "running"
    if stage.module_ids and all(module_id in state.deterministic_results for module_id in stage.module_ids):
        return "complete"
    if any(module_id in state.deterministic_results for module_id in stage.module_ids):
        return "partial"
    if any(status in {"blocked", "error", "failed"} for status in statuses):
        return "blocked"
    return "waiting"


def build_stage_payloads(
    state: DesignState,
    presentation_status: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    stages: List[Dict[str, Any]] = []
    for index, stage in enumerate(DEMO_STAGES, start=1):
        status = stage_status(stage, state, presentation_status)
        stages.append(
            {
                "index": index,
                "id": stage.id,
                "title": stage.title,
                "plainEnglish": stage.plain_english,
                "moduleIds": stage.module_ids,
                "status": status,
                "generatedArtifact": stage.generated_artifact,
                "evidenceLevel": stage.evidence_level,
            }
        )
    return stages


def build_evidence_badges(state: DesignState) -> List[Dict[str, str]]:
    badges: List[Dict[str, str]] = []
    bom = safe_dict(safe_dict(state.deterministic_results.get("component_search")).get("selected_bom"))
    loss = safe_dict(safe_dict(state.deterministic_results.get("loss_thermal")).get("loss_breakdown"))
    sim = safe_dict(safe_dict(state.deterministic_results.get("open_loop_sim")).get("simulation_result"))
    control = safe_dict(safe_dict(state.deterministic_results.get("closed_loop_control")).get("control_result"))
    library = safe_dict(state.deterministic_results.get("library_pcb_mechanical"))
    test_report = safe_dict(state.deterministic_results.get("test_report"))
    evaluation = safe_dict(safe_dict(state.deterministic_results.get("validation")).get("evaluation_summary"))
    if bom:
        badges.append({"label": "BOM", "sourceType": str(bom.get("source") or "mock catalog"), "confidence": "demo", "signoffStatus": "not signoff"})
    if loss:
        badges.append({"label": "Loss/Thermal", "sourceType": "first-order estimate", "confidence": str(loss.get("confidence") or "medium"), "signoffStatus": "not signoff"})
    if sim:
        badges.append({"label": "Waveforms", "sourceType": str(sim.get("backend") or "synthetic"), "confidence": "demo-backed", "signoffStatus": "not signoff"})
    if control:
        badges.append({"label": "Control", "sourceType": "analytical loop model", "confidence": "demo-backed", "signoffStatus": "not signoff"})
    if library:
        badges.append({"label": "PCB/3D", "sourceType": "placeholder plan", "confidence": "low", "signoffStatus": "needs signoff"})
    if test_report:
        badges.append({"label": "Test Workflow", "sourceType": "fake lab workflow", "confidence": "demo-backed", "signoffStatus": "not signoff"})
    if evaluation:
        badges.append({"label": "Validation", "sourceType": str(evaluation.get("overall_status") or "partial"), "confidence": "honest gaps", "signoffStatus": "needs signoff"})
    if not badges:
        badges.append({"label": "Evidence", "sourceType": "waiting for run", "confidence": "none", "signoffStatus": "not started"})
    return badges


def build_metrics(state: DesignState) -> Dict[str, Any]:
    spec = state.spec
    loss = safe_dict(safe_dict(state.deterministic_results.get("loss_thermal")).get("loss_breakdown"))
    thermal = safe_dict(safe_dict(state.deterministic_results.get("loss_thermal")).get("thermal_result"))
    sim = safe_dict(safe_dict(state.deterministic_results.get("open_loop_sim")).get("simulation_result"))
    sim_metrics = safe_dict(sim.get("metrics"))
    control = safe_dict(safe_dict(state.deterministic_results.get("closed_loop_control")).get("control_result"))
    evaluation = safe_dict(safe_dict(state.deterministic_results.get("validation")).get("evaluation_summary"))
    test_report = safe_dict(state.deterministic_results.get("test_report"))
    missing_data = safe_list(evaluation.get("missing_data"))
    ripple_value = _float_or_none(sim_metrics.get("vout_ripple_mv_pp"))
    transient_value = _float_or_none(sim_metrics.get("vout_transient_deviation_mv"))
    eff_value = _float_or_none(loss.get("efficiency_percent"))
    total_loss_value = _float_or_none(loss.get("total_loss_w"))
    temp_value = _float_or_none(thermal.get("max_junction_temp_c"))
    return {
        "health": {
            "label": str(evaluation.get("overall_status") or state.workflow_status or "idle").replace("_", " ").title(),
            "tone": "pass" if evaluation.get("overall_status") == "pass" else "warn" if state.deterministic_results else "neutral",
        },
        "efficiency": {"value": eff_value, "display": fmt_num(eff_value, "%"), "target": spec.target_efficiency_percent, "tone": pass_fail_tone(eff_value >= spec.target_efficiency_percent if eff_value is not None else None)},
        "totalLoss": {"value": total_loss_value, "display": fmt_num(total_loss_value, " W"), "target": spec.max_total_loss_w, "tone": pass_fail_tone(total_loss_value <= spec.max_total_loss_w if total_loss_value is not None else None)},
        "maxTemp": {"value": temp_value, "display": fmt_num(temp_value, " C"), "target": 105.0, "tone": temp_tone(temp_value)},
        "voutRipple": {"value": ripple_value, "display": fmt_num(ripple_value, " mVpp"), "target": spec.output_ripple_mv_pp, "tone": pass_fail_tone(ripple_value <= spec.output_ripple_mv_pp if ripple_value is not None else None)},
        "transient": {"value": transient_value, "display": fmt_num(transient_value, " mV"), "target": spec.transient_deviation_mv, "tone": pass_fail_tone(transient_value <= spec.transient_deviation_mv if transient_value is not None else None)},
        "ilPeak": {"value": _float_or_none(sim_metrics.get("inductor_peak_a")), "display": fmt_num(sim_metrics.get("inductor_peak_a"), " A"), "target": safe_dict(sim.get("limit_bands")).get("il_current_limit_placeholder_a"), "tone": "neutral"},
        "phaseMargin": {"value": _float_or_none(control.get("phase_margin_deg")), "display": fmt_num(control.get("phase_margin_deg"), " deg"), "target": 45.0, "tone": pass_fail_tone(_float_or_none(control.get("phase_margin_deg")) >= 45.0 if control else None)},
        "missingData": {"value": len(missing_data), "display": str(len(missing_data)), "tone": "pass" if not missing_data and evaluation else "warn" if missing_data else "neutral"},
    }


def build_energy_story(state: DesignState) -> Dict[str, Any]:
    spec = state.spec
    loss = safe_dict(safe_dict(state.deterministic_results.get("loss_thermal")).get("loss_breakdown"))
    thermal = safe_dict(safe_dict(state.deterministic_results.get("loss_thermal")).get("thermal_result"))
    sim = safe_dict(safe_dict(state.deterministic_results.get("open_loop_sim")).get("simulation_result"))
    sim_metrics = safe_dict(sim.get("metrics"))
    output_power = _float_or_none(loss.get("output_power_w")) or spec.output_voltage_v * spec.output_current_a
    total_loss = _float_or_none(loss.get("total_loss_w"))
    input_power = _float_or_none(loss.get("input_power_w")) or (output_power + total_loss if total_loss is not None else None)
    efficiency = _float_or_none(loss.get("efficiency_percent"))
    return {
        "headline": "The agent turns a product ask into a reviewable power-stage draft.",
        "cards": [
            {"label": "Output Power", "value": output_power, "display": fmt_num(output_power, " W"), "tone": "neutral", "explain": "Useful 5V power delivered to the USB-C load."},
            {"label": "Input Power", "value": input_power, "display": fmt_num(input_power, " W"), "tone": "neutral", "explain": "Input watts estimated from output power plus loss."},
            {"label": "Lost As Heat", "value": total_loss, "display": fmt_num(total_loss, " W"), "tone": pass_fail_tone(total_loss <= spec.max_total_loss_w if total_loss is not None else None), "explain": "Watts that must be removed through silicon, copper, magnetics, and airflow."},
            {"label": "Efficiency", "value": efficiency, "display": fmt_num(efficiency, "%"), "tone": pass_fail_tone(efficiency >= spec.target_efficiency_percent if efficiency is not None else None), "explain": "First-order estimate at nominal input and full load."},
            {"label": "Hot Spot", "value": _float_or_none(thermal.get("max_junction_temp_c")), "display": fmt_num(thermal.get("max_junction_temp_c"), " C"), "tone": temp_tone(thermal.get("max_junction_temp_c")), "explain": "Highest estimated component temperature."},
            {"label": "Ripple", "value": _float_or_none(sim_metrics.get("vout_ripple_mv_pp")), "display": fmt_num(sim_metrics.get("vout_ripple_mv_pp"), " mVpp"), "tone": pass_fail_tone((_float_or_none(sim_metrics.get("vout_ripple_mv_pp")) or 1e9) <= spec.output_ripple_mv_pp if sim_metrics else None), "explain": "How much the 5V rail wiggles in steady state."},
        ],
    }


def build_waveforms(state: DesignState, max_points: int = 900) -> Dict[str, Any]:
    spec = state.spec
    sim = safe_dict(safe_dict(state.deterministic_results.get("open_loop_sim")).get("simulation_result"))
    waveforms = safe_dict(sim.get("waveforms"))
    metrics = safe_dict(sim.get("metrics"))
    limits = safe_dict(sim.get("limit_bands"))
    control = safe_dict(safe_dict(state.deterministic_results.get("closed_loop_control")).get("control_result"))
    bode = safe_dict(safe_dict(state.deterministic_results.get("closed_loop_control")).get("bode_plot"))
    bode_metrics = safe_dict(bode.get("metrics"))
    control_bode = {
        "available": bool(bode.get("freq_hz") and bode.get("mag_db") and bode.get("phase_deg")),
        "sourceBadge": str(bode.get("source") or "missing: run Design Control"),
        "series": {
            "freq_hz": _downsample(bode.get("freq_hz", []), 260),
            "mag_db": _downsample(bode.get("mag_db", []), 260),
            "phase_deg": _downsample(bode.get("phase_deg", []), 260),
        },
        "metrics": {
            "crossover_hz": bode_metrics.get("crossover_hz") or control.get("crossover_hz"),
            "phase_margin_deg": bode_metrics.get("phase_margin_deg") or control.get("phase_margin_deg"),
            "gain_margin_db": bode_metrics.get("gain_margin_db"),
            "phase_crossover_hz": bode_metrics.get("phase_crossover_hz"),
        },
        "summary": (
            f"Control designed: crossover {fmt_hz(bode_metrics.get('crossover_hz') or control.get('crossover_hz'))}, "
            f"phase margin {fmt_num(bode_metrics.get('phase_margin_deg') or control.get('phase_margin_deg'), ' deg')}."
            if control or bode
            else "Run Design Control to add closed-loop Bode stability."
        ),
    }
    if not waveforms:
        return {
            "available": False,
            "sourceBadge": "missing: run open-loop simulation",
            "metrics": {},
            "limits": {
                "nominal_v": spec.output_voltage_v,
                "ripple_upper_v": spec.output_voltage_v + spec.output_ripple_mv_pp / 2000.0,
                "ripple_lower_v": spec.output_voltage_v - spec.output_ripple_mv_pp / 2000.0,
                "transient_upper_v": spec.output_voltage_v + spec.transient_deviation_mv / 1000.0,
                "transient_lower_v": spec.output_voltage_v - spec.transient_deviation_mv / 1000.0,
            },
            "series": {},
            "events": [],
            "controlBode": control_bode,
        }
    return {
        "available": True,
        "sourceBadge": str(sim.get("source_badge") or f"{sim.get('backend', 'synthetic')}: not signoff"),
        "metrics": metrics,
        "limits": limits,
        "events": safe_list(sim.get("events")),
        "series": {
            "time_us": _downsample(waveforms.get("time_us", []), max_points),
            "vout_v": _downsample(waveforms.get("vout_v", []), max_points),
            "il_a": _downsample(waveforms.get("il_a", []), max_points),
            "switch_v": _downsample(waveforms.get("switch_v", []), max_points),
            "load_current_a": _downsample(waveforms.get("load_current_a", []), max_points),
            "duty_command": _downsample(waveforms.get("duty_command", []), max_points),
        },
        "controlBode": control_bode,
    }


GROUP_ORDER = ["MOSFET", "Inductor", "Capacitors", "PCB/PDN", "Other"]


def _loss_scale(key: str, current_ratio: float, vin_ratio: float) -> float:
    key_lower = key.lower()
    if "gate_drive" in key_lower:
        return 1.0
    if "coss" in key_lower:
        return vin_ratio * vin_ratio
    if "switching" in key_lower or "body_diode" in key_lower or "reverse_recovery" in key_lower:
        return current_ratio * vin_ratio
    if "core" in key_lower:
        return 0.45 + 0.55 * (current_ratio**1.45)
    return current_ratio * current_ratio


def _scaled_items(items: Dict[str, Any], current_a: float, full_current_a: float, vin_v: float, vin_nom_v: float) -> Dict[str, float]:
    current_ratio = current_a / max(full_current_a, 1e-9)
    vin_ratio = vin_v / max(vin_nom_v, 1e-9)
    scaled: Dict[str, float] = {}
    for key, value in items.items():
        number = _float_or_none(value)
        if number is not None:
            scaled[key] = max(0.0, number * _loss_scale(str(key), current_ratio, vin_ratio))
    return scaled


def _group_losses(items: Dict[str, float]) -> Dict[str, float]:
    grouped = {name: 0.0 for name in GROUP_ORDER}
    for key, value in items.items():
        text = key.lower()
        if "mosfet" in text or "gate" in text or "coss" in text or "body_diode" in text or "reverse_recovery" in text or "switching" in text:
            grouped["MOSFET"] += value
        elif "inductor" in text:
            grouped["Inductor"] += value
        elif "cap" in text:
            grouped["Capacitors"] += value
        elif "pcb" in text or "pdn" in text or "cable" in text or "contact" in text:
            grouped["PCB/PDN"] += value
        else:
            grouped["Other"] += value
    return grouped


def _efficiency(vout_v: float, current_a: float, total_loss_w: float) -> float:
    output_power = max(0.0, vout_v * current_a)
    if output_power <= 0.0:
        return 0.0
    return output_power / (output_power + total_loss_w) * 100.0


def build_loss_thermal(state: DesignState) -> Dict[str, Any]:
    spec = state.spec
    loss = safe_dict(safe_dict(state.deterministic_results.get("loss_thermal")).get("loss_breakdown"))
    thermal = safe_dict(safe_dict(state.deterministic_results.get("loss_thermal")).get("thermal_result"))
    items = safe_dict(loss.get("items_w"))
    full_current = max(0.05, float(spec.output_current_a))
    start_current = min(full_current, max(0.10, full_current * 0.10))
    currents = [round(start_current + (full_current - start_current) * idx / 40.0, 4) for idx in range(41)]
    vin_values: List[float] = []
    for vin in [spec.input_voltage_min_v, spec.input_voltage_nominal_v, spec.input_voltage_max_v]:
        if all(abs(float(vin) - existing) > 0.01 for existing in vin_values):
            vin_values.append(float(vin))
    sweep_efficiency = []
    sweep_loss = []
    peak_record: Dict[str, Any] = {"efficiency": -1.0, "current": full_current, "items": {}, "loss": 0.0}
    nominal_vin = float(spec.input_voltage_nominal_v)
    for vin in vin_values:
        efficiencies = []
        for current in currents:
            point_items = _scaled_items(items, current, full_current, vin, nominal_vin)
            total_loss = sum(point_items.values())
            eff = _efficiency(float(spec.output_voltage_v), current, total_loss)
            efficiencies.append(round(eff, 3))
            if abs(vin - nominal_vin) < 0.01 and eff > peak_record["efficiency"]:
                peak_record = {"efficiency": eff, "current": current, "items": point_items, "loss": total_loss}
        sweep_efficiency.append({"vin": vin, "label": f"{vin:g}V efficiency", "values": efficiencies})
    group_series = {name: [] for name in GROUP_ORDER}
    total_losses = []
    for current in currents:
        point_items = _scaled_items(items, current, full_current, nominal_vin, nominal_vin)
        grouped = _group_losses(point_items)
        for name in GROUP_ORDER:
            group_series[name].append(round(grouped[name], 5))
        total_losses.append(round(sum(point_items.values()), 5))
    for name in GROUP_ORDER:
        sweep_loss.append({"group": name, "values": group_series[name]})
    full_items = _scaled_items(items, full_current, full_current, nominal_vin, nominal_vin)
    if not peak_record["items"]:
        peak_record = {"efficiency": 0.0, "current": full_current, "items": full_items, "loss": sum(full_items.values())}
    peak_grouped = _group_losses(peak_record["items"])
    full_grouped = _group_losses(full_items)
    return {
        "available": bool(items or safe_dict(thermal.get("component_temps_c"))),
        "sourceBadge": "first-order estimate; not signoff" if items else "missing",
        "items": [{"key": key, "value": value, "display": fmt_num(value, " W", 4)} for key, value in items.items()],
        "sweep": {
            "currentsA": currents,
            "efficiency": sweep_efficiency,
            "lossGroups": sweep_loss,
            "totalLossW": total_losses,
            "efficiencyTarget": spec.target_efficiency_percent,
            "lossTargetW": spec.max_total_loss_w,
        },
        "pies": [
            {
                "title": "Peak Efficiency Loss",
                "subtitle": f"{peak_record['current']:.2f}A, {peak_record['efficiency']:.1f}% eff",
                "items": [{"label": key, "value": round(value, 5), "display": fmt_num(value, " W", 3)} for key, value in peak_grouped.items() if value > 1e-5],
            },
            {
                "title": "Full-Power Loss",
                "subtitle": f"{full_current:.2f}A, {_efficiency(spec.output_voltage_v, full_current, sum(full_items.values())):.1f}% eff",
                "items": [{"label": key, "value": round(value, 5), "display": fmt_num(value, " W", 3)} for key, value in full_grouped.items() if value > 1e-5],
            },
        ],
        "thermal": {
            "componentTempsC": [
                {"key": key, "label": key.replace("_", " ").title(), "value": value, "display": fmt_num(value, " C", 1), "tone": temp_tone(value)}
                for key, value in safe_dict(thermal.get("component_temps_c")).items()
            ],
            "maxJunctionTempC": thermal.get("max_junction_temp_c"),
            "warnings": safe_list(thermal.get("warnings")),
            "modelNotes": safe_list(thermal.get("model_notes")),
            "legend": "Green <85C, yellow 85-105C, orange 105-125C, red >=125C. Model: Tj = Ta + P x RthetaJA_eff; board and airflow dependent.",
        },
    }


def _part_summary(part: Dict[str, Any]) -> str:
    if not part:
        return "Not selected yet."
    params = safe_dict(part.get("key_params"))
    keys = [
        "vds_v",
        "rds_on_mohm_25c",
        "qg_nc",
        "inductance_uh",
        "dcr_mohm_25c",
        "isat_a",
        "capacitance_uf_effective",
        "voltage_rating_v",
        "esr_mohm",
    ]
    highlights = [f"{key}={params[key]}" for key in keys if key in params]
    return f"{part.get('manufacturer', '-')} {part.get('mpn', '-')}; {', '.join(highlights[:5])}; source={part.get('source', 'unknown')}"


def build_design_rationale(state: DesignState) -> Dict[str, Any]:
    spec = state.spec
    spec_result = safe_dict(state.deterministic_results.get("spec_analyzer"))
    candidate = safe_dict(spec_result.get("selected_candidate"))
    bom = safe_dict(safe_dict(state.deterministic_results.get("component_search")).get("selected_bom"))
    loss = safe_dict(safe_dict(state.deterministic_results.get("loss_thermal")).get("loss_breakdown"))
    loss_items = safe_dict(loss.get("items_w"))
    derived = safe_dict(safe_dict(state.deterministic_results.get("loss_thermal")).get("derived"))
    thermal = safe_dict(safe_dict(state.deterministic_results.get("loss_thermal")).get("thermal_result"))
    sim = safe_dict(safe_dict(state.deterministic_results.get("open_loop_sim")).get("simulation_result"))
    sim_metrics = safe_dict(sim.get("metrics"))
    control = safe_dict(safe_dict(state.deterministic_results.get("closed_loop_control")).get("control_result"))
    bode = safe_dict(safe_dict(state.deterministic_results.get("closed_loop_control")).get("bode_plot"))
    evaluation = safe_dict(safe_dict(state.deterministic_results.get("validation")).get("evaluation_summary"))
    library = safe_dict(state.deterministic_results.get("library_pcb_mechanical"))

    duty = candidate.get("duty_nominal", spec.output_voltage_v / max(spec.input_voltage_nominal_v, 1e-9))
    formulas = [
        {"checkpoint": "Duty cycle", "formula": "D = Vout / Vin", "value": f"D = {spec.output_voltage_v:g} / {spec.input_voltage_nominal_v:g} = {fmt_num(duty, '', 4)}"},
        {"checkpoint": "Inductor ripple", "formula": "Delta IL = Vout x (1 - D) / (L x fsw)", "value": f"Vin(max) ripple = {fmt_num(derived.get('inductor_ripple_a_at_vin_max'), ' A', 4)}; L = {fmt_num(candidate.get('inductor_uh'), ' uH')}; fsw = {fmt_hz(candidate.get('switching_frequency_hz'))}"},
        {"checkpoint": "Inductor RMS", "formula": "IL,rms = sqrt(Iout^2 + DeltaIL^2 / 12)", "value": f"IL,rms = {fmt_num(derived.get('inductor_rms_a'), ' A', 4)}"},
        {"checkpoint": "Input cap RMS", "formula": "ICIN,rms = Iout x sqrt(D x (1 - D))", "value": f"ICIN,rms = {fmt_num(derived.get('input_cap_rms_a'), ' A', 4)}"},
        {"checkpoint": "Output cap ripple current", "formula": "ICOUT,rms = DeltaIL / (2 x sqrt(3))", "value": f"ICOUT,rms = {fmt_num(derived.get('output_cap_rms_a'), ' A', 4)}"},
        {"checkpoint": "MOSFET conduction", "formula": "Pcond = IL,rms^2 x Rds_on(T) x duty_fraction", "value": f"HS={fmt_num(loss_items.get('hs_mosfet_conduction'), ' W', 4)}; LS={fmt_num(loss_items.get('ls_mosfet_conduction'), ' W', 4)}"},
        {"checkpoint": "MOSFET switching", "formula": "Psw = 0.5 x Vin x Iout x (tr + tf) x fsw", "value": f"HS overlap={fmt_num(loss_items.get('hs_switching_overlap'), ' W', 4)}"},
        {"checkpoint": "Gate and Coss losses", "formula": "Pgate = Qg x Vdrive x fsw; Pcoss = 0.5 x Coss x Vin^2 x fsw", "value": f"Gate={fmt_num(loss_items.get('gate_drive'), ' W', 4)}; Coss/Eoss={fmt_num(loss_items.get('coss_eoss'), ' W', 4)}"},
        {"checkpoint": "Dead-time and recovery", "formula": "Pdeadtime ~= Iout x Vf x tdead x 2 x fsw; Qrr is placeholder in v1", "value": f"Body diode={fmt_num(loss_items.get('body_diode_deadtime'), ' W', 4)}; Qrr placeholder={fmt_num(loss_items.get('reverse_recovery_placeholder'), ' W', 4)}"},
        {"checkpoint": "Magnetics and caps", "formula": "PDCR = IL,rms^2 x DCR(T); PESR = Irms^2 x ESR", "value": f"Inductor DCR={fmt_num(loss_items.get('inductor_dcr'), ' W', 4)}; core={fmt_num(loss_items.get('inductor_core_placeholder'), ' W', 4)}; caps={fmt_num(loss_items.get('output_cap_esr'), ' W', 4)} + {fmt_num(loss_items.get('input_cap_rms_esr'), ' W', 4)}"},
        {"checkpoint": "PCB / PDN", "formula": "PPDN = Iout^2 x Rpath", "value": f"PCB/PDN/contact={fmt_num(loss_items.get('pcb_pdn_cable_contact'), ' W', 4)}"},
        {"checkpoint": "Thermal", "formula": "Tj = Ta + Pcomponent x RthetaJA_eff", "value": f"Max estimate = {fmt_num(thermal.get('max_junction_temp_c'), ' C')}; RthetaJA is board/airflow dependent"},
        {"checkpoint": "Control seed", "formula": "fc target from plant estimate; PM from analytical loop-gain sweep", "value": f"fc={fmt_hz(control.get('crossover_hz'))}; PM={fmt_num(control.get('phase_margin_deg'), ' deg')}; source={bode.get('source', 'not run')}"},
    ]

    sections = [
        {
            "title": "Problem Framing",
            "bullets": [
                "Application: vehicle/industrial USB-C 15W synchronous buck charger, chosen because the demo maps to a real market use case.",
                f"Target: {spec.input_voltage_min_v:g}-{spec.input_voltage_max_v:g}V input to {spec.output_voltage_v:g}V / {spec.output_current_a:g}A output.",
                f"Acceptance: ripple <= {spec.output_ripple_mv_pp:g}mVpp, transient <= {spec.transient_deviation_mv:g}mV, efficiency >= {spec.target_efficiency_percent:g}%, loss <= {spec.max_total_loss_w:g}W.",
            ],
        },
        {
            "title": "Architecture And Choices",
            "bullets": [
                f"Topology: {candidate.get('topology', 'not selected')}. Reason: high-efficiency step-down from 9-36V to 5V/3A with low conduction loss.",
                f"Switching frequency: {fmt_hz(candidate.get('switching_frequency_hz'))}. Reason: balances magnetic size, switching loss, and control bandwidth for a demo charger.",
                f"Power-stage start point: L={fmt_num(candidate.get('inductor_uh'), ' uH')}, Cout={fmt_num(candidate.get('output_cap_uf'), ' uF')}, Cin={fmt_num(candidate.get('input_cap_uf'), ' uF')}.",
                f"KiCad/FreeCAD status: {library.get('source', 'not run') if library else 'not run'}; real land pattern and 3D output still require signoff.",
            ],
        },
        {
            "title": "Component Rationale",
            "bullets": [
                f"High-side MOSFET: {_part_summary(safe_dict(bom.get('high_side_mosfet')))}",
                f"Low-side MOSFET: {_part_summary(safe_dict(bom.get('low_side_mosfet')))}",
                f"Inductor: {_part_summary(safe_dict(bom.get('inductor')))}",
                f"Input capacitor: {_part_summary(safe_dict(bom.get('input_capacitor')))}",
                f"Output capacitor: {_part_summary(safe_dict(bom.get('output_capacitor')))}",
            ],
        },
        {
            "title": "Results To Double Check First",
            "bullets": [
                f"Loss: total {fmt_num(loss.get('total_loss_w'), ' W')}, efficiency {fmt_num(loss.get('efficiency_percent'), '%')}.",
                f"Thermal: max estimate {fmt_num(thermal.get('max_junction_temp_c'), ' C')}; board and airflow assumptions dominate accuracy.",
                f"Waveform: ripple {fmt_num(sim_metrics.get('vout_ripple_mv_pp'), ' mVpp')}, transient {fmt_num(sim_metrics.get('vout_transient_deviation_mv'), ' mV')}, IL peak {fmt_num(sim_metrics.get('inductor_peak_a'), ' A')}.",
                f"Control: PM {fmt_num(control.get('phase_margin_deg'), ' deg')} from analytical synthetic loop-gain, not tool-backed signoff.",
            ],
        },
    ]

    return {
        "intro": "Concise engineering rationale for human double-check. It lists choices, equations, current values, sources, and review gaps without turning into a full report.",
        "workflowStatus": state.workflow_status,
        "sourceBadges": [
            str(loss.get("confidence", "loss not run")),
            str(sim.get("source_badge", "waveform source missing")),
            str(bode.get("source", "control not run")),
        ],
        "sections": sections,
        "formulas": formulas,
        "risks": [humanize_risk(item) for item in safe_list(evaluation.get("risks"))[:8]],
        "missingData": [humanize_missing_data(item) for item in safe_list(evaluation.get("missing_data"))],
        "nextActions": safe_list(evaluation.get("recommended_next_actions"))[:6],
    }


def build_risk_summary(state: DesignState) -> Dict[str, Any]:
    evaluation = safe_dict(safe_dict(state.deterministic_results.get("validation")).get("evaluation_summary"))
    risks = [humanize_risk(item) for item in safe_list(evaluation.get("risks"))]
    missing_data = [humanize_missing_data(item) for item in safe_list(evaluation.get("missing_data"))]
    return {
        "overallStatus": str(evaluation.get("overall_status") or state.workflow_status),
        "issues": safe_list(evaluation.get("issues")),
        "risks": risks,
        "missingData": missing_data,
        "recommendedNextActions": safe_list(evaluation.get("recommended_next_actions")),
        "approvalGates": safe_list(evaluation.get("approval_gates")),
    }


def _format_param(key: str, value: Any) -> str:
    label = key.replace("_", " ")
    if isinstance(value, float):
        return f"{label}: {value:g}"
    return f"{label}: {value}"


def build_execution_plan(state: DesignState) -> Dict[str, Any]:
    spec_result = safe_dict(state.deterministic_results.get("spec_analyzer"))
    plan = safe_list(spec_result.get("execution_plan"))
    return {
        "available": bool(plan),
        "items": plan,
        "sourceType": str(spec_result.get("sourceType") or "deterministic_demo_planner"),
        "realCapabilityStatus": str(spec_result.get("realCapabilityStatus") or "waiting_for_specifications"),
        "notice": "Demo execution plan. Real external tool execution is not connected in this version.",
    }


def build_parts_catalog(state: DesignState) -> Dict[str, Any]:
    component = safe_dict(state.deterministic_results.get("component_search"))
    bom = safe_dict(component.get("selected_bom"))
    part_order = [
        "high_side_mosfet",
        "low_side_mosfet",
        "inductor",
        "input_capacitor",
        "output_capacitor",
    ]
    items = []
    for key in part_order:
        part = safe_dict(bom.get(key))
        if not part:
            continue
        params = safe_dict(part.get("key_params"))
        quantity = int(part.get("quantity") or 1)
        unit_price = _float_or_none(part.get("unit_price_usd")) or 0.0
        items.append(
            {
                "role": _human_label(key),
                "category": str(part.get("category") or key),
                "mpn": str(part.get("mpn") or "-"),
                "manufacturer": str(part.get("manufacturer") or "-"),
                "keyParams": [_format_param(param_key, value) for param_key, value in params.items()],
                "unitPriceUsd": unit_price,
                "quantity": quantity,
                "lineTotalUsd": round(unit_price * quantity, 4),
                "stockQty": part.get("stock_qty"),
                "footprint": str(part.get("footprint") or "-"),
                "datasheetUrl": str(part.get("datasheet_url") or ""),
                "supplierLinks": safe_dict(part.get("supplier_links")),
                "compliance": str(part.get("compliance") or "demo_requirement_check"),
                "sourceType": str(part.get("source") or "fake_digikey_mouser"),
                "realCapabilityStatus": "not_connected",
            }
        )
    return {
        "available": bool(items),
        "items": items,
        "totalCostUsd": round(sum(float(item["lineTotalUsd"]) for item in items), 4),
        "candidateCounts": safe_dict(component.get("candidate_counts")),
        "selectionRules": safe_list(component.get("selection_rules")),
        "distributorQueries": safe_list(component.get("distributor_queries")),
        "sourceType": str(component.get("sourceType") or "fake_digikey_mouser"),
        "realCapabilityStatus": str(component.get("realCapabilityStatus") or "not_connected"),
        "notice": "Demo data only. DigiKey and Mouser APIs are not connected yet.",
    }


def build_analysis_summary(state: DesignState) -> Dict[str, Any]:
    artifact_result = safe_dict(state.deterministic_results.get("power_buck_analysis"))
    if artifact_result:
        return artifact_result
    result = safe_dict(state.deterministic_results.get("loss_thermal"))
    loss = safe_dict(result.get("loss_breakdown"))
    thermal = safe_dict(result.get("thermal_result"))
    derived = safe_dict(result.get("derived"))
    return {
        "available": bool(loss or thermal),
        "cards": safe_list(result.get("summary_cards")),
        "lossItems": [{"label": key.replace("_", " "), "display": fmt_num(value, " W", 4)} for key, value in safe_dict(loss.get("items_w")).items()],
        "derived": [{"label": key.replace("_", " "), "value": value} for key, value in derived.items()],
        "thermal": {
            "maxJunctionTempC": thermal.get("max_junction_temp_c"),
            "componentTempsC": safe_dict(thermal.get("component_temps_c")),
            "warnings": safe_list(thermal.get("warnings")),
        },
        "sourceType": str(result.get("sourceType") or "first_order_demo_model"),
        "realCapabilityStatus": str(result.get("realCapabilityStatus") or "demo_estimate_not_signoff"),
        "notice": "First-order demo estimate. Real thermal simulation and measured validation are not connected yet.",
    }


def build_simulation_artifacts(state: DesignState) -> Dict[str, Any]:
    result = safe_dict(state.deterministic_results.get("power_buck_simulation"))
    if result:
        return result
    return {
        "available": False,
        "status": "waiting",
        "source": "not_run",
        "adapter": {"adapter": "ngspice", "connected": False, "message": "Select a simulator adapter and run Simulation."},
        "plots": [],
        "rawOutputs": [],
        "metrics": {},
        "comparison": {},
    }


def build_control_plan(state: DesignState) -> Dict[str, Any]:
    result = safe_dict(state.deterministic_results.get("closed_loop_control"))
    plan = safe_dict(result.get("control_plan"))
    control = safe_dict(result.get("control_result"))
    if plan:
        return {"available": True, **plan}
    return {
        "available": bool(control),
        "controlMode": "waiting_for_control_design",
        "compensatorType": "-",
        "parameters": [],
        "validation": [],
        "sourceType": "analytical_synthetic_loop_gain",
        "realCapabilityStatus": "waiting_for_control",
        "notice": "Run Control to generate the demo control plan.",
    }


def build_pcb_automation_plan(state: DesignState) -> Dict[str, Any]:
    result = safe_dict(state.deterministic_results.get("library_pcb_mechanical"))
    plan = safe_dict(result.get("library_generation_plan"))
    return {
        "available": bool(result),
        "selectedParts": safe_list(plan.get("selected_parts")),
        "automationSteps": safe_list(result.get("automation_steps")),
        "libraryPlan": plan,
        "downstreamInterfaces": safe_dict(result.get("downstream_interfaces")),
        "sourceType": str(result.get("sourceType") or "fake_kicad_jlcpcb_pipeline"),
        "realCapabilityStatus": str(result.get("realCapabilityStatus") or "not_connected"),
        "notice": str(result.get("capabilityNotice") or "Demo data only. KiCad/JLCPCB automation is not connected yet."),
    }


def _test_module_card(
    *,
    module_id: str,
    label: str,
    title: str,
    result: Dict[str, Any],
    summary: str,
    outputs_label: str,
) -> Dict[str, Any]:
    outputs = safe_list(result.get("outputs"))
    if outputs:
        output_preview = ", ".join(str(safe_dict(item).get("label") or safe_dict(item).get("path") or "-") for item in outputs[:3])
    else:
        output_preview = "Waiting for demo run."
    return {
        "id": module_id,
        "label": label,
        "title": title,
        "status": str(result.get("status") or "waiting"),
        "summary": summary,
        "outputsLabel": outputs_label,
        "outputPreview": output_preview,
        "outputs": outputs,
        "sourceType": str(result.get("sourceType") or "fake_lab_workflow"),
        "realCapabilityStatus": str(result.get("realCapabilityStatus") or "not_connected"),
        "notice": str(result.get("notice") or "Demo data / Not connected."),
    }


def build_test_workflow(state: DesignState) -> Dict[str, Any]:
    codes = safe_dict(state.deterministic_results.get("embedded_coding_download"))
    tuning = safe_dict(state.deterministic_results.get("closed_loop_tuning"))
    data = safe_dict(state.deterministic_results.get("efficiency_logging"))
    report = safe_dict(state.deterministic_results.get("test_report"))
    cards = [
        _test_module_card(
            module_id="embedded_coding_download",
            label="Codes",
            title="Embedded Coding Download",
            result=codes,
            summary="Generate firmware, flash the returned board, verify device identity, and keep a bring-up transcript.",
            outputs_label="Firmware and flash evidence",
        ),
        _test_module_card(
            module_id="closed_loop_tuning",
            label="Tuning",
            title="Auto Closed-Loop Tuning",
            result=tuning,
            summary="Sweep compensator settings on the bench and pick parameters that meet transient and stability targets.",
            outputs_label="Tuning sweep and final registers",
        ),
        _test_module_card(
            module_id="efficiency_logging",
            label="Data",
            title="Auto Efficiency Logging",
            result=data,
            summary="Record efficiency, ripple, thermal, and instrument metadata across the operating range.",
            outputs_label="Efficiency, ripple, and thermal logs",
        ),
        _test_module_card(
            module_id="test_report",
            label="Report",
            title="Auto Test Report",
            result=report,
            summary="Build the post-prototype report with evidence links, pass/fail checks, and revision actions.",
            outputs_label="Report and revision actions",
        ),
    ]
    return {
        "available": bool(codes or tuning or data or report),
        "cards": cards,
        "codes": codes,
        "tuning": tuning,
        "data": data,
        "report": report,
        "sourceType": "fake_lab_workflow",
        "realCapabilityStatus": "not_connected",
        "notice": "Demo data only. Firmware flashing, closed-loop bench tuning, efficiency logging, and lab report automation are not connected yet.",
    }


def build_fake_capability_notices(state: DesignState) -> List[Dict[str, str]]:
    candidates = [
        ("Specifications", build_execution_plan(state)),
        ("Parts", build_parts_catalog(state)),
        ("Analysis", build_analysis_summary(state)),
        ("Control", build_control_plan(state)),
        ("PCB", build_pcb_automation_plan(state)),
        ("Test", build_test_workflow(state)),
    ]
    notices: List[Dict[str, str]] = []
    for label, payload in candidates:
        status = str(payload.get("realCapabilityStatus") or "")
        if status and status != "connected":
            notices.append(
                {
                    "module": label,
                    "sourceType": str(payload.get("sourceType") or "demo_data"),
                    "realCapabilityStatus": status,
                    "notice": str(payload.get("notice") or "Demo data / Not connected."),
                }
            )
    return notices


def build_investor_summary(state: DesignState) -> str:
    spec = state.spec
    loss = safe_dict(safe_dict(state.deterministic_results.get("loss_thermal")).get("loss_breakdown"))
    thermal = safe_dict(safe_dict(state.deterministic_results.get("loss_thermal")).get("thermal_result"))
    sim = safe_dict(safe_dict(state.deterministic_results.get("open_loop_sim")).get("simulation_result"))
    control = safe_dict(safe_dict(state.deterministic_results.get("closed_loop_control")).get("control_result"))
    evaluation = safe_dict(safe_dict(state.deterministic_results.get("validation")).get("evaluation_summary"))
    test_report = safe_dict(state.deterministic_results.get("test_report"))
    pieces = [f"{spec.input_voltage_min_v:g}-{spec.input_voltage_max_v:g}V to {spec.output_voltage_v:g}V/{spec.output_current_a:g}A charger draft"]
    if loss:
        pieces.append(f"{fmt_num(loss.get('efficiency_percent'), '%')} efficiency estimate")
        pieces.append(f"{fmt_num(loss.get('total_loss_w'), ' W')} loss")
    if thermal:
        pieces.append(f"{fmt_num(thermal.get('max_junction_temp_c'), ' C')} hot-spot estimate")
    if sim:
        pieces.append(f"{fmt_num(safe_dict(sim.get('metrics')).get('vout_ripple_mv_pp'), ' mVpp')} ripple")
    if control:
        pieces.append(f"{fmt_num(control.get('phase_margin_deg'), ' deg')} phase margin")
    if test_report:
        pieces.append("fake post-prototype test workflow completed")
    if evaluation:
        pieces.append(f"{len(evaluation.get('missing_data', []) or [])} known gaps")
    if len(pieces) == 1:
        return "Ready to run the investor demo and generate the first reviewable hardware draft."
    return "; ".join(pieces) + "."


def build_investor_snapshot_markdown(state: DesignState) -> str:
    metrics = build_metrics(state)
    energy = build_energy_story(state)
    badges = build_evidence_badges(state)
    rationale = build_design_rationale(state)
    risk_summary = build_risk_summary(state)
    lines = [
        "# AutoEE Investor Snapshot",
        "",
        f"Prompt: {INVESTOR_DEMO_PROMPT}",
        "",
        "## Summary",
        build_investor_summary(state),
        "",
        "## Key Metrics",
    ]
    for key, value in metrics.items():
        lines.append(f"- {key}: {safe_dict(value).get('display', safe_dict(value).get('label', '-'))}")
    lines.extend(["", "## Energy Story"])
    for card in energy["cards"]:
        lines.append(f"- {card['label']}: {card['display']} - {card['explain']}")
    lines.extend(["", "## Generated In This Run"])
    for artifact in state.artifacts:
        lines.append(f"- {artifact.kind}: {artifact.path} ({artifact.source})")
    if not state.artifacts:
        lines.append("- No artifact files generated yet.")
    lines.extend(["", "## Evidence Labels"])
    for badge in badges:
        lines.append(f"- {badge['label']}: {badge['sourceType']}, confidence={badge['confidence']}, status={badge['signoffStatus']}")
    lines.extend(["", "## Design Rationale Quick Check"])
    for section in rationale["sections"]:
        lines.append(f"### {section['title']}")
        for bullet in section["bullets"]:
            lines.append(f"- {bullet}")
    lines.extend(["", "## Formulas"])
    for row in rationale["formulas"]:
        lines.append(f"- {row['checkpoint']}: `{row['formula']}` -> {row['value']}")
    lines.extend(["", "## Risks And Missing Data"])
    for item in risk_summary["risks"][:10]:
        lines.append(f"- Risk: {item}")
    for item in risk_summary["missingData"][:20]:
        lines.append(f"- Missing: {item}")
    if not risk_summary["risks"] and not risk_summary["missingData"]:
        lines.append("- Run validation to populate risk and missing-data summary.")
    lines.extend(
        [
            "",
            "## Honesty Note",
            "This snapshot is a demo-backed engineering draft. Mock catalog, synthetic simulation, placeholder PCB/3D, and not-signoff labels are intentionally preserved.",
            "",
        ]
    )
    return "\n".join(lines)


def build_web_state(
    state: DesignState,
    presentation_status: Optional[Dict[str, str]] = None,
    running: bool = False,
    started_at: Optional[float] = None,
) -> Dict[str, Any]:
    stages = build_stage_payloads(state, presentation_status)
    current_stage = next((stage for stage in stages if stage["status"] != "complete"), stages[-1] if stages else None)
    if running:
        current_stage = next((stage for stage in stages if stage["status"] == "running"), current_stage)
    elapsed_s = max(0.0, time.monotonic() - started_at) if started_at else 0.0
    risk_summary = build_risk_summary(state)
    module_statuses = {
        module_id: module_status(module_id, state, presentation_status)
        for stage in DEMO_STAGES
        for module_id in stage.module_ids
    }
    return {
        "prompt": INVESTOR_DEMO_PROMPT,
        "spec": state.spec.to_dict(),
        "workflowStatus": state.workflow_status,
        "running": running,
        "elapsedSeconds": round(elapsed_s, 1),
        "currentStage": current_stage,
        "investorSummary": build_investor_summary(state),
        "stages": stages,
        "moduleStatus": module_statuses,
        "moduleNarration": INVESTOR_NARRATION,
        "metrics": build_metrics(state),
        "energy": build_energy_story(state),
        "waveforms": build_waveforms(state),
        "lossThermal": build_loss_thermal(state),
        "designRationale": build_design_rationale(state),
        "riskSummary": risk_summary,
        "executionPlan": build_execution_plan(state),
        "partsCatalog": build_parts_catalog(state),
        "analysisSummary": build_analysis_summary(state),
        "simulationArtifacts": build_simulation_artifacts(state),
        "controlPlan": build_control_plan(state),
        "pcbAutomationPlan": build_pcb_automation_plan(state),
        "testWorkflow": build_test_workflow(state),
        "fakeCapabilityNotices": build_fake_capability_notices(state),
        "evidenceBadges": build_evidence_badges(state),
        "progressEvents": [event.to_dict() for event in state.progress_events[-80:]],
        "rawState": state.to_dict(),
        "nextActions": risk_summary.get("recommendedNextActions", [])[:6] or [
            "Run the offline workflow.",
            "Replace mock BOM with distributor-backed sourcing.",
            "Replace synthetic waveforms with PLECS/LTspice before signoff.",
        ],
    }
