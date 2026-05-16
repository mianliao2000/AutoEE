from __future__ import annotations

import argparse
import html
import json
import math
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from PyQt5 import QtCore, QtGui, QtWidgets

import matplotlib

matplotlib.use("Qt5Agg")
matplotlib.rcParams.update(
    {
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 8,
        "figure.titlesize": 12,
    }
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from autoee_demo.core import AutoEEAgent, DesignState, ProjectSpec
from autoee_demo.model_backend import ModelBackendSettings, ModelManager
from autoee_demo.ui.model_backend_dialog import ModelBackendDialog


SPEC_FIELDS = [
    ("input_voltage_min_v", "Vin min", "V", 0.1, 200.0, 2, 1.0),
    ("input_voltage_nominal_v", "Vin nom", "V", 0.1, 200.0, 2, 1.0),
    ("input_voltage_max_v", "Vin max", "V", 0.1, 200.0, 2, 1.0),
    ("output_voltage_v", "Vout", "V", 0.1, 100.0, 2, 0.1),
    ("output_current_a", "Iout", "A", 0.01, 200.0, 2, 0.1),
    ("output_ripple_mv_pp", "Ripple", "mVpp", 1.0, 5000.0, 1, 5.0),
    ("transient_step_a", "Load step", "A", 0.01, 200.0, 2, 0.1),
    ("transient_deviation_mv", "Transient", "mV", 1.0, 5000.0, 1, 10.0),
    ("target_efficiency_percent", "Eff min", "%", 1.0, 99.9, 2, 0.5),
    ("ambient_temp_c", "Ambient", "C", -40.0, 150.0, 1, 1.0),
    ("max_total_loss_w", "Loss max", "W", 0.01, 500.0, 2, 0.1),
]

RUN_ALL_TERMS = ["run all", "full demo", "workflow", "demo", "start", "execute", "完整", "全部", "跑通", "执行"]
STOP_TERMS = ["stop", "cancel", "停止", "中止"]
RESET_TERMS = ["reset", "clear", "重置", "清空"]


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


def temp_color(value: Any) -> str:
    try:
        temp = float(value)
    except (TypeError, ValueError):
        return "#64748b"
    if temp < 85.0:
        return "#047857"
    if temp < 105.0:
        return "#ca8a04"
    if temp < 125.0:
        return "#c2410c"
    return "#dc2626"


def safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def modules_until(agent: AutoEEAgent, module_id: str) -> List[str]:
    out: List[str] = []
    for skill in agent.skills:
        out.append(skill.module_id)
        if skill.module_id == module_id:
            break
    return out


def modules_for_prompt(agent: AutoEEAgent, prompt: str) -> Optional[List[str]]:
    text = prompt.strip().lower()
    original = prompt.strip()
    if not text:
        return None
    if any(term in text or term in original for term in RUN_ALL_TERMS):
        return [skill.module_id for skill in agent.skills]
    if any(term in text or term in original for term in ["bode", "control", "closed loop", "pid", "补偿", "闭环", "控制"]):
        return modules_until(agent, "closed_loop_control")
    if any(term in text or term in original for term in ["simulation", "simulate", "waveform", "plecs", "ltspice", "仿真", "波形"]):
        return modules_until(agent, "open_loop_sim")
    if any(term in text or term in original for term in ["thermal", "loss", "efficiency", "温升", "热", "损耗", "效率"]):
        return modules_until(agent, "loss_thermal")
    if any(term in text or term in original for term in ["bom", "digikey", "mosfet", "inductor", "capacitor", "器件", "电感", "电容"]):
        return modules_until(agent, "component_search")
    if any(term in text or term in original for term in ["report", "报告", "导出"]):
        return modules_until(agent, "report_generator")
    if any(term in text or term in original for term in ["eval", "evaluate", "validation", "risk", "missing"]):
        return modules_until(agent, "validation")
    return None


def local_design_summary(state: DesignState) -> str:
    spec = state.spec
    loss = safe_dict(safe_dict(state.deterministic_results.get("loss_thermal")).get("loss_breakdown"))
    thermal = safe_dict(safe_dict(state.deterministic_results.get("loss_thermal")).get("thermal_result"))
    sim = safe_dict(safe_dict(state.deterministic_results.get("open_loop_sim")).get("simulation_result"))
    control = safe_dict(safe_dict(state.deterministic_results.get("closed_loop_control")).get("control_result"))
    evaluation = safe_dict(safe_dict(state.deterministic_results.get("validation")).get("evaluation_summary"))
    lines = [
        "Local AutoEE summary:",
        f"- Target: {spec.input_voltage_min_v:g}-{spec.input_voltage_max_v:g}V input to {spec.output_voltage_v:g}V/{spec.output_current_a:g}A output.",
    ]
    if loss:
        lines.append(
            f"- Loss/efficiency: {fmt_num(loss.get('total_loss_w'), ' W')} total loss, "
            f"{fmt_num(loss.get('efficiency_percent'), '%')} estimated efficiency."
        )
    if thermal:
        lines.append(f"- Thermal: max first-order temperature estimate {fmt_num(thermal.get('max_junction_temp_c'), ' C')}.")
    if sim:
        metrics = safe_dict(sim.get("metrics"))
        lines.append(
            f"- Open-loop synthetic sim: ripple {fmt_num(metrics.get('vout_ripple_mv_pp'), ' mVpp')}, "
            f"IL peak {fmt_num(metrics.get('inductor_peak_a'), ' A')}."
        )
    if control:
        lines.append(
            f"- Control seed: fc {fmt_hz(control.get('crossover_hz'))}, "
            f"phase margin {fmt_num(control.get('phase_margin_deg'), ' deg')}."
        )
    if evaluation:
        lines.append(
            f"- Evaluation: overall {evaluation.get('overall_status', '-')}, "
            f"{len(evaluation.get('missing_data', []) or [])} missing data items."
        )
    if not state.deterministic_results:
        lines.append("- No design modules have run yet. Ask me to run the full demo, loss estimate, simulation, or Bode/control workflow.")
    lines.append("- Data source: deterministic v1 modules with mock/synthetic placeholders where commercial tools are not configured.")
    return "\n".join(lines)


@dataclass(frozen=True)
class DemoStage:
    id: str
    title: str
    explanation: str
    module_ids: List[str]
    artifact: str
    evidence_level: str

    def status_for(self, state: DesignState) -> str:
        statuses = [state.module_status.get(module_id, "") for module_id in self.module_ids]
        if any(status == "running" for status in statuses):
            return "running"
        if self.module_ids and all(module_id in state.deterministic_results for module_id in self.module_ids):
            return "complete"
        if any(module_id in state.deterministic_results for module_id in self.module_ids):
            return "partial"
        return "waiting"


@dataclass(frozen=True)
class EvidenceBadge:
    label: str
    source_type: str
    confidence: str
    signoff_status: str


@dataclass
class DemoNarrativeState:
    current_stage_id: str
    elapsed_s: float
    stages: List[DemoStage]
    stage_statuses: Dict[str, str]
    badges: List[EvidenceBadge]
    final_summary: str


DEMO_STAGES = [
    DemoStage(
        "understand_specs",
        "Understand Specs",
        "Translate the product ask into electrical, thermal, and acceptance constraints.",
        ["spec_analyzer"],
        "Constraint matrix",
        "deterministic estimate",
    ),
    DemoStage(
        "select_parts",
        "Select Parts",
        "Search and rank MOSFETs, magnetics, and capacitors for the target charger.",
        ["component_search"],
        "Initial BOM",
        "mock catalog",
    ),
    DemoStage(
        "loss_thermal",
        "Estimate Loss/Thermal",
        "Predict where watts are lost and whether parts get too hot.",
        ["loss_thermal"],
        "Loss and thermal model",
        "first-order estimate",
    ),
    DemoStage(
        "waveforms",
        "Simulate Waveforms",
        "Show whether 5V stays stable during ripple and load-step stress.",
        ["open_loop_sim"],
        "Vout, IL, SW, load waveforms",
        "synthetic simulation",
    ),
    DemoStage(
        "control",
        "Design Control",
        "Create a first closed-loop control seed and stability view.",
        ["closed_loop_control"],
        "Bode and control seed",
        "analytical estimate",
    ),
    DemoStage(
        "package",
        "Build Package",
        "Assemble PCB/3D plan, risk evaluation, report, and reusable memory.",
        ["library_pcb_mechanical", "validation", "report_generator", "skill_memory"],
        "Design package draft",
        "needs signoff",
    ),
]


INVESTOR_NARRATION = {
    "spec_analyzer": "I converted the product ask into engineering constraints: voltage range, ripple, transient, efficiency, and thermal targets.",
    "component_search": "I selected a first-pass power stage from a mock distributor catalog and kept the source label visible.",
    "loss_thermal": "I estimated where power turns into heat, then translated that into component temperature risk.",
    "open_loop_sim": "I generated Buck waveforms so investors can see 5V regulation, inductor current, and load-step behavior.",
    "emag_maxwell": "I created the EM and magnetics job placeholder so the future real workflow has a clear handoff.",
    "closed_loop_control": "I produced a first control seed and Bode stability view instead of leaving compensation as a manual afterthought.",
    "library_pcb_mechanical": "I prepared the KiCad, PCB, and 3D generation plan while marking real library output as future signoff work.",
    "validation": "I evaluated the run honestly: what is complete, what is mock, what is synthetic, and what still needs proof.",
    "report_generator": "I exported the design state and report package so the run becomes a reviewable engineering artifact.",
    "skill_memory": "I saved reusable workflow memory so future designs can start from this experience.",
}


def build_demo_narrative_state(state: DesignState, started_at: Optional[float] = None) -> DemoNarrativeState:
    statuses = {stage.id: stage.status_for(state) for stage in DEMO_STAGES}
    current = next((stage.id for stage in DEMO_STAGES if statuses[stage.id] != "complete"), DEMO_STAGES[-1].id)
    elapsed = max(0.0, time.monotonic() - started_at) if started_at else 0.0
    badges = build_evidence_badges(state)
    return DemoNarrativeState(
        current_stage_id=current,
        elapsed_s=elapsed,
        stages=list(DEMO_STAGES),
        stage_statuses=statuses,
        badges=badges,
        final_summary=build_investor_summary(state),
    )


def build_evidence_badges(state: DesignState) -> List[EvidenceBadge]:
    badges: List[EvidenceBadge] = []
    bom = safe_dict(safe_dict(state.deterministic_results.get("component_search")).get("selected_bom"))
    loss = safe_dict(safe_dict(state.deterministic_results.get("loss_thermal")).get("loss_breakdown"))
    sim = safe_dict(safe_dict(state.deterministic_results.get("open_loop_sim")).get("simulation_result"))
    control = safe_dict(safe_dict(state.deterministic_results.get("closed_loop_control")).get("control_result"))
    library = safe_dict(state.deterministic_results.get("library_pcb_mechanical"))
    evaluation = safe_dict(safe_dict(state.deterministic_results.get("validation")).get("evaluation_summary"))
    if bom:
        badges.append(EvidenceBadge("BOM", str(bom.get("source") or "mock catalog"), "demo", "not signoff"))
    if loss:
        badges.append(EvidenceBadge("Loss/Thermal", "first-order estimate", str(loss.get("confidence") or "medium"), "not signoff"))
    if sim:
        badges.append(EvidenceBadge("Waveforms", str(sim.get("backend") or "synthetic"), "demo-backed", "not signoff"))
    if control:
        badges.append(EvidenceBadge("Control", "analytical loop model", "demo-backed", "not signoff"))
    if library:
        badges.append(EvidenceBadge("PCB/3D", "placeholder plan", "low", "needs signoff"))
    if evaluation:
        badges.append(EvidenceBadge("Validation", str(evaluation.get("overall_status") or "partial"), "honest gaps", "needs signoff"))
    if not badges:
        badges.append(EvidenceBadge("Evidence", "waiting for run", "none", "not started"))
    return badges


def build_investor_summary(state: DesignState) -> str:
    spec = state.spec
    loss = safe_dict(safe_dict(state.deterministic_results.get("loss_thermal")).get("loss_breakdown"))
    thermal = safe_dict(safe_dict(state.deterministic_results.get("loss_thermal")).get("thermal_result"))
    sim = safe_dict(safe_dict(state.deterministic_results.get("open_loop_sim")).get("simulation_result"))
    control = safe_dict(safe_dict(state.deterministic_results.get("closed_loop_control")).get("control_result"))
    evaluation = safe_dict(safe_dict(state.deterministic_results.get("validation")).get("evaluation_summary"))
    pieces = [f"{spec.input_voltage_min_v:g}-{spec.input_voltage_max_v:g}V to {spec.output_voltage_v:g}V/{spec.output_current_a:g}A charger draft"]
    if loss:
        pieces.append(f"{fmt_num(loss.get('efficiency_percent'), '%')} efficiency estimate")
        pieces.append(f"{fmt_num(loss.get('total_loss_w'), ' W')} loss")
    if thermal:
        pieces.append(f"{fmt_num(thermal.get('max_junction_temp_c'), ' C')} hot-spot estimate")
    if sim:
        metrics = safe_dict(sim.get("metrics"))
        pieces.append(f"{fmt_num(metrics.get('vout_ripple_mv_pp'), ' mVpp')} ripple")
    if control:
        pieces.append(f"{fmt_num(control.get('phase_margin_deg'), ' deg')} phase margin")
    if evaluation:
        missing = len(evaluation.get("missing_data", []) or [])
        pieces.append(f"{missing} signoff gaps identified")
    return "; ".join(pieces) + "."


class StatTile(QtWidgets.QFrame):
    clicked = QtCore.pyqtSignal(str)

    def __init__(self, label: str, value: str = "-", tone: str = "neutral", metric_key: str = ""):
        super().__init__()
        self.metric_key = metric_key
        self.setObjectName("StatTile")
        self.setProperty("tone", tone)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setMinimumHeight(50)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(2)
        self.label = QtWidgets.QLabel(label)
        self.label.setObjectName("StatLabel")
        self.value = QtWidgets.QLabel(value)
        self.value.setObjectName("StatValue")
        self.value.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(self.label)
        layout.addWidget(self.value)

    def set_value(self, value: str, tone: str = "neutral") -> None:
        self.value.setText(value)
        self.setProperty("tone", tone)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self.clicked.emit(self.metric_key or self.label.text())
        super().mousePressEvent(event)


class DesignOverviewPanel(QtWidgets.QTextBrowser):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DesignOverview")
        self.setOpenExternalLinks(True)
        self.setReadOnly(True)

    @staticmethod
    def _pill(text: str, tone: str = "neutral") -> str:
        colors = {
            "pass": ("#ecfdf5", "#047857"),
            "warn": ("#fffbeb", "#b45309"),
            "fail": ("#fef2f2", "#dc2626"),
            "neutral": ("#f1f5f9", "#64748b"),
        }
        bg, fg = colors.get(tone, colors["neutral"])
        return f'<span style="background:{bg}; color:{fg}; border:1px solid {fg}; border-radius:4px; padding:2px 6px;">{html.escape(text)}</span>'

    def update_from_state(self, state: DesignState) -> None:
        spec = state.spec
        loss = safe_dict(safe_dict(state.deterministic_results.get("loss_thermal")).get("loss_breakdown"))
        thermal = safe_dict(safe_dict(state.deterministic_results.get("loss_thermal")).get("thermal_result"))
        sim = safe_dict(safe_dict(state.deterministic_results.get("open_loop_sim")).get("simulation_result"))
        sim_metrics = safe_dict(sim.get("metrics"))
        control = safe_dict(safe_dict(state.deterministic_results.get("closed_loop_control")).get("control_result"))
        evaluation = safe_dict(safe_dict(state.deterministic_results.get("validation")).get("evaluation_summary"))
        risks = list(evaluation.get("risks", []) or [])
        missing = list(evaluation.get("missing_data", []) or [])
        next_actions = list(evaluation.get("recommended_next_actions", []) or [])
        eval_status = str(evaluation.get("overall_status") or state.workflow_status or "idle")
        source = str(sim.get("source_badge") or "missing: waveform not available")
        source_tone = "warn" if "synthetic" in source else "neutral"
        health_tone = {"pass": "pass", "partial": "warn", "missing": "fail", "complete": "warn"}.get(eval_status, "neutral")

        ripple_result = fmt_num(sim_metrics.get("vout_ripple_mv_pp"), " mVpp")
        transient_result = fmt_num(sim_metrics.get("vout_transient_deviation_mv"), " mV")
        il_peak = fmt_num(sim_metrics.get("inductor_peak_a"), " A")
        efficiency = fmt_num(loss.get("efficiency_percent"), "%")
        max_temp = fmt_num(thermal.get("max_junction_temp_c"), " C")
        pm = fmt_num(control.get("phase_margin_deg"), " deg")
        missing_text = f"{len(missing)} missing data items" if evaluation else "evaluation not run"
        if not next_actions:
            next_actions = ["Run Full Demo to generate evidence, then review Evaluation."]

        html_text = f"""
        <div style="font-size:10.5pt; line-height:1.35;">
        <h1 style="color:#0f172a; margin-bottom:4px;">AutoEE is trying to build a real 15W USB-C Buck charger</h1>
        <p style="color:#334155; margin-top:0;">
          The job is simple to say and hard to execute: take noisy car/industrial input
          <b>{spec.input_voltage_min_v:g}-{spec.input_voltage_max_v:g}V</b>, make a clean
          <b>{spec.output_voltage_v:g}V / {spec.output_current_a:g}A</b> USB rail, stay cool, and prove the design is not fantasy.
          {self._pill(eval_status.title(), health_tone)} {self._pill(source, source_tone)}
        </p>
        <p style="color:#475569;">
          A Buck converter is basically a fast electronic valve. The MOSFET turns the input on and off,
          the inductor turns those pulses into smooth current, and the output capacitor catches the bumps
          when the load jumps from light load to phone-charging load.
        </p>
        <table width="100%" cellspacing="12">
          <tr>
            <td style="vertical-align:top; background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; padding:12px;">
              <h2 style="color:#047857; margin-top:0;">Can the output stay calm?</h2>
              <p><b>Target:</b> 5V rail, ripple <= {spec.output_ripple_mv_pp:g} mVpp, load-step movement <= {spec.transient_deviation_mv:g} mV.</p>
              <p><b>Current result:</b> ripple {ripple_result}; transient movement {transient_result}.</p>
              <p><b>How to read the waveform:</b> Vout should look almost flat; the load-step marker is where the charger suddenly has to deliver much more current.</p>
              <p><b>Next action:</b> replace this synthetic run with PLECS/LTspice and compare the numbers.</p>
            </td>
            <td style="vertical-align:top; background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; padding:12px;">
              <h2 style="color:#2563eb; margin-top:0;">Are the parts being abused?</h2>
              <p><b>Inductor current:</b> peak {il_peak}. That number decides saturation margin and current-limit headroom.</p>
              <p><b>Loss:</b> {fmt_num(loss.get('total_loss_w'), ' W')} disappears as heat at full load.</p>
              <p><b>Hot spot:</b> <span style="color:{temp_color(thermal.get('max_junction_temp_c'))}; font-size:13pt; font-weight:700;">{max_temp}</span></p>
              <p><b>Plain English:</b> if current stress or temperature is wrong, the schematic may work on paper and fail on the bench.</p>
            </td>
          </tr>
          <tr>
            <td style="vertical-align:top; background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; padding:12px;">
              <h2 style="color:#b45309; margin-top:0;">Is it commercially believable?</h2>
              <p><b>Efficiency target:</b> >= {spec.target_efficiency_percent:g}%.</p>
              <p><b>Current estimate:</b> {efficiency}; every lost watt becomes heat, heatsink area, copper area, or customer pain.</p>
              <p><b>Control:</b> phase margin {pm}; this is the early answer to "will it ring or recover cleanly?"</p>
            </td>
            <td style="vertical-align:top; background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; padding:12px;">
              <h2 style="color:#dc2626; margin-top:0;">What still needs proof?</h2>
              <p><b>Evaluation:</b> {missing_text}</p>
              <p><b>Top risk:</b> {html.escape(risks[0] if risks else "No risks recorded yet.")}</p>
              <p><b>Recommended next action:</b> {html.escape(next_actions[0])}</p>
              <p style="color:#64748b;">Synthetic data keeps the demo runnable without external tools, but it is not sign-off evidence.</p>
            </td>
          </tr>
        </table>
        </div>
        """
        self.setHtml(html_text)


class DesignRationalePanel(QtWidgets.QTextBrowser):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DesignRationale")
        self.setOpenExternalLinks(True)
        self.setReadOnly(True)

    @staticmethod
    def _pill(text: str, tone: str = "neutral") -> str:
        colors = {
            "pass": ("#ecfdf5", "#047857"),
            "warn": ("#fffbeb", "#b45309"),
            "fail": ("#fef2f2", "#dc2626"),
            "info": ("#eff6ff", "#2563eb"),
            "neutral": ("#f1f5f9", "#64748b"),
        }
        bg, fg = colors.get(tone, colors["neutral"])
        return f'<span style="background:{bg}; color:{fg}; border:1px solid {fg}; border-radius:4px; padding:2px 6px;">{html.escape(text)}</span>'

    @staticmethod
    def _part_summary(part: Dict[str, Any]) -> str:
        if not part:
            return "Not selected yet."
        params = safe_dict(part.get("key_params"))
        highlights = []
        for key in ["vds_v", "rds_on_mohm_25c", "qg_nc", "inductance_uh", "dcr_mohm_25c", "isat_a", "capacitance_uf_effective", "voltage_rating_v", "esr_mohm"]:
            if key in params:
                highlights.append(f"{key}={params[key]}")
        source = part.get("source", "unknown")
        return f"{html.escape(str(part.get('manufacturer', '-')))} {html.escape(str(part.get('mpn', '-')))}; {html.escape(', '.join(highlights[:5]))}; source={html.escape(str(source))}"

    @staticmethod
    def _loss_item(items: Dict[str, Any], key: str) -> str:
        value = items.get(key)
        return fmt_num(value, " W", 4) if value is not None else "missing"

    def update_from_state(self, state: DesignState) -> None:
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
        fsw = candidate.get("switching_frequency_hz")
        inductor = candidate.get("inductor_uh")
        output_cap = candidate.get("output_cap_uf")
        input_cap = candidate.get("input_cap_uf")
        ripple_a = derived.get("inductor_ripple_a_at_vin_max")
        il_rms = derived.get("inductor_rms_a")
        input_cap_rms = derived.get("input_cap_rms_a")
        output_cap_rms = derived.get("output_cap_rms_a")
        missing = list(evaluation.get("missing_data", []) or [])
        risks = list(evaluation.get("risks", []) or [])
        next_actions = list(evaluation.get("recommended_next_actions", []) or [])
        source_badge = sim.get("source_badge", "waveform source missing")
        library_source = library.get("source", "placeholder") if library else "not run"

        formula_rows = [
            (
                "Duty cycle",
                "D = Vout / Vin",
                f"D = {spec.output_voltage_v:g} / {spec.input_voltage_nominal_v:g} = {fmt_num(duty, '', 4)}",
            ),
            (
                "Inductor ripple",
                "Delta IL = Vout x (1 - D) / (L x fsw)",
                f"Vin(max) ripple estimate = {fmt_num(ripple_a, ' A', 4)}; L = {fmt_num(inductor, ' uH')}, fsw = {fmt_hz(fsw)}",
            ),
            (
                "Inductor RMS",
                "IL,rms = sqrt(Iout^2 + DeltaIL^2 / 12)",
                f"IL,rms = {fmt_num(il_rms, ' A', 4)}",
            ),
            (
                "Input cap RMS",
                "ICIN,rms = Iout x sqrt(D x (1 - D))",
                f"ICIN,rms = {fmt_num(input_cap_rms, ' A', 4)}",
            ),
            (
                "Output cap ripple current",
                "ICOUT,rms = DeltaIL / (2 x sqrt(3))",
                f"ICOUT,rms = {fmt_num(output_cap_rms, ' A', 4)}; Cout start point = {fmt_num(output_cap, ' uF')}",
            ),
            (
                "MOSFET conduction",
                "Pcond = IL,rms^2 x Rds_on(T) x duty_fraction",
                f"HS={self._loss_item(loss_items, 'hs_mosfet_conduction')}; LS={self._loss_item(loss_items, 'ls_mosfet_conduction')}",
            ),
            (
                "MOSFET switching",
                "Psw = 0.5 x Vin x Iout x (tr + tf) x fsw",
                f"HS overlap={self._loss_item(loss_items, 'hs_switching_overlap')}",
            ),
            (
                "Gate and Coss losses",
                "Pgate = Qg x Vdrive x fsw; Pcoss = 0.5 x Coss x Vin^2 x fsw",
                f"Gate={self._loss_item(loss_items, 'gate_drive')}; Coss/Eoss={self._loss_item(loss_items, 'coss_eoss')}",
            ),
            (
                "Dead-time and recovery",
                "Pdeadtime ~= Iout x Vf x tdead x 2 x fsw; Qrr is placeholder in v1",
                f"Body diode={self._loss_item(loss_items, 'body_diode_deadtime')}; Qrr placeholder={self._loss_item(loss_items, 'reverse_recovery_placeholder')}",
            ),
            (
                "Magnetics and caps",
                "PDCR = IL,rms^2 x DCR(T); PESR = Irms^2 x ESR",
                f"Inductor DCR={self._loss_item(loss_items, 'inductor_dcr')}; core={self._loss_item(loss_items, 'inductor_core_placeholder')}; caps={self._loss_item(loss_items, 'output_cap_esr')} + {self._loss_item(loss_items, 'input_cap_rms_esr')}",
            ),
            (
                "PCB / PDN",
                "PPDN = Iout^2 x Rpath",
                f"PCB/PDN/contact={self._loss_item(loss_items, 'pcb_pdn_cable_contact')}",
            ),
            (
                "Thermal",
                "Tj = Ta + Pcomponent x RthetaJA_eff",
                f"Max estimated temperature = {fmt_num(thermal.get('max_junction_temp_c'), ' C')}; RthetaJA is board/airflow dependent",
            ),
            (
                "Control seed",
                "fc target from plant estimate; PM from analytical loop-gain sweep",
                f"fc={fmt_hz(control.get('crossover_hz'))}; PM={fmt_num(control.get('phase_margin_deg'), ' deg')}; source={html.escape(str(bode.get('source', 'not run')))}",
            ),
        ]

        formula_html = "".join(
            f"""
            <tr>
              <td><b>{html.escape(name)}</b></td>
              <td><code>{html.escape(formula)}</code></td>
              <td>{html.escape(check)}</td>
            </tr>
            """
            for name, formula, check in formula_rows
        )
        top_risks = "".join(f"<li>{html.escape(str(item))}</li>" for item in risks[:6]) or "<li>No risks recorded yet.</li>"
        top_actions = "".join(f"<li>{html.escape(str(item))}</li>" for item in next_actions[:4]) or "<li>Run validation and report generation.</li>"

        html_text = f"""
        <div style="font-size:10pt; line-height:1.35; color:#0f172a;">
          <h1 style="margin:0 0 4px 0;">Design Rationale Quick Check</h1>
          <p style="color:#475569; margin-top:0;">
            Concise design reasoning for human double-check. This is not a long report and does not expose hidden model chain-of-thought;
            it lists engineering choices, equations, current values, sources, and review gaps.
          </p>
          <p>
            {self._pill(state.workflow_status.title(), 'info')}
            {self._pill(str(loss.get('confidence', 'loss not run')), 'neutral')}
            {self._pill(str(source_badge), 'warn' if 'synthetic' in str(source_badge) else 'neutral')}
          </p>

          <h2>1. Problem Framing</h2>
          <ul>
            <li><b>Application:</b> vehicle/industrial USB-C 15W synchronous Buck charger. This is a market-relevant demo, not a random lab point.</li>
            <li><b>Target:</b> {spec.input_voltage_min_v:g}-{spec.input_voltage_max_v:g}V input -> {spec.output_voltage_v:g}V / {spec.output_current_a:g}A output.</li>
            <li><b>Acceptance:</b> ripple <= {spec.output_ripple_mv_pp:g}mVpp, transient <= {spec.transient_deviation_mv:g}mV, efficiency >= {spec.target_efficiency_percent:g}%, loss <= {spec.max_total_loss_w:g}W.</li>
          </ul>

          <h2>2. Architecture And Key Choices</h2>
          <ul>
            <li><b>Topology:</b> {html.escape(str(candidate.get('topology', 'not selected')))}. Reason: high-efficiency step-down from 9-36V to 5V/3A with low conduction loss.</li>
            <li><b>Switching frequency:</b> {fmt_hz(fsw)}. Reason: balances magnetics size, switching loss, and control bandwidth for a demo charger.</li>
            <li><b>Power stage start point:</b> L={fmt_num(inductor, ' uH')}, Cout={fmt_num(output_cap, ' uF')}, Cin={fmt_num(input_cap, ' uF')}.</li>
            <li><b>Datasheet/library path:</b> KiCad/FreeCAD output is currently {html.escape(str(library_source))}; real land pattern and 3D output still require signoff.</li>
          </ul>

          <h2>3. Component Selection Rationale</h2>
          <ul>
            <li><b>High-side MOSFET:</b> {self._part_summary(safe_dict(bom.get('high_side_mosfet')))}</li>
            <li><b>Low-side MOSFET:</b> {self._part_summary(safe_dict(bom.get('low_side_mosfet')))}</li>
            <li><b>Inductor:</b> {self._part_summary(safe_dict(bom.get('inductor')))}</li>
            <li><b>Input capacitor:</b> {self._part_summary(safe_dict(bom.get('input_capacitor')))}</li>
            <li><b>Output capacitor:</b> {self._part_summary(safe_dict(bom.get('output_capacitor')))}</li>
          </ul>

          <h2>4. Formula And Calculation Checkpoints</h2>
          <table width="100%" cellspacing="0" cellpadding="7" style="border-collapse:collapse;">
            <tr style="background:#f1f5f9;">
              <th align="left">Checkpoint</th><th align="left">Formula Used</th><th align="left">Current Value / Review Note</th>
            </tr>
            {formula_html}
          </table>

          <h2>5. Results To Double Check First</h2>
          <ul>
            <li><b>Loss:</b> total {fmt_num(loss.get('total_loss_w'), ' W')}, efficiency {fmt_num(loss.get('efficiency_percent'), '%')}.</li>
            <li><b>Thermal:</b> max estimate {fmt_num(thermal.get('max_junction_temp_c'), ' C')}; board and airflow assumptions dominate accuracy.</li>
            <li><b>Waveform:</b> ripple {fmt_num(sim_metrics.get('vout_ripple_mv_pp'), ' mVpp')}, transient {fmt_num(sim_metrics.get('vout_transient_deviation_mv'), ' mV')}, IL peak {fmt_num(sim_metrics.get('inductor_peak_a'), ' A')}.</li>
            <li><b>Control:</b> PM {fmt_num(control.get('phase_margin_deg'), ' deg')} from analytical synthetic loop-gain, not tool-backed signoff.</li>
          </ul>

          <h2>6. Known Review Gaps</h2>
          <ul>{top_risks}</ul>
          <p><b>Missing data count:</b> {len(missing)}. Main next actions:</p>
          <ul>{top_actions}</ul>
        </div>
        """
        self.setHtml(html_text)


class InvestorDemoPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("InvestorDemo")
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.hero = QtWidgets.QTextBrowser()
        self.hero.setObjectName("InvestorHero")
        self.hero.setReadOnly(True)
        self.hero.setMaximumHeight(172)
        layout.addWidget(self.hero)

        action_row = QtWidgets.QHBoxLayout()
        self.prompt_label = QtWidgets.QLabel(INVESTOR_DEMO_PROMPT)
        self.prompt_label.setObjectName("DemoPrompt")
        self.btn_run_demo = QtWidgets.QPushButton("Run Demo")
        self.btn_run_demo.setObjectName("PrimaryButton")
        self.btn_reset_demo = QtWidgets.QPushButton("Reset Demo")
        self.btn_export_snapshot = QtWidgets.QPushButton("Export Investor Snapshot")
        action_row.addWidget(self.prompt_label, 1)
        action_row.addWidget(self.btn_run_demo)
        action_row.addWidget(self.btn_reset_demo)
        action_row.addWidget(self.btn_export_snapshot)
        layout.addLayout(action_row)

        center = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        center.setChildrenCollapsible(False)
        self.stage_view = QtWidgets.QTextBrowser()
        self.stage_view.setObjectName("InvestorStage")
        self.stage_view.setReadOnly(True)
        self.package_view = QtWidgets.QTextBrowser()
        self.package_view.setObjectName("InvestorPackage")
        self.package_view.setReadOnly(True)
        center.addWidget(self.stage_view)
        center.addWidget(self.package_view)
        center.setSizes([720, 360])
        layout.addWidget(center, 1)

        bottom = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        bottom.setChildrenCollapsible(False)
        self.energy_view = QtWidgets.QTextBrowser()
        self.energy_view.setObjectName("InvestorEnergy")
        self.energy_view.setReadOnly(True)
        self.evidence_view = QtWidgets.QTextBrowser()
        self.evidence_view.setObjectName("InvestorEvidence")
        self.evidence_view.setReadOnly(True)
        bottom.addWidget(self.energy_view)
        bottom.addWidget(self.evidence_view)
        bottom.setSizes([620, 460])
        bottom.setMaximumHeight(220)
        layout.addWidget(bottom)

    @staticmethod
    def _pill(text: str, tone: str = "neutral") -> str:
        colors = {
            "complete": ("#ecfdf5", "#047857"),
            "running": ("#fffbeb", "#b45309"),
            "partial": ("#eff6ff", "#2563eb"),
            "waiting": ("#f1f5f9", "#64748b"),
            "warn": ("#fffbeb", "#b45309"),
            "neutral": ("#f1f5f9", "#64748b"),
        }
        bg, fg = colors.get(tone, colors["neutral"])
        return f'<span style="background:{bg}; color:{fg}; border:1px solid {fg}; border-radius:4px; padding:3px 7px;">{html.escape(text)}</span>'

    def _stage_html(self, narrative: DemoNarrativeState) -> str:
        rows = []
        for index, stage in enumerate(narrative.stages, start=1):
            status = narrative.stage_statuses.get(stage.id, "waiting")
            is_current = stage.id == narrative.current_stage_id and status != "complete"
            border = "#10b981" if status == "complete" else "#f59e0b" if is_current or status == "running" else "#cbd5e1"
            headline = f"{index}. {html.escape(stage.title)}"
            rows.append(
                f"""
                <div style="border:1px solid {border}; border-radius:8px; padding:9px 11px; margin:6px 0; background:#ffffff;">
                  <div style="font-size:12pt; color:#0f172a; font-weight:700;">{headline} {self._pill(status.title(), status)}</div>
                  <div style="font-size:9.7pt; color:#334155; margin-top:4px;">{html.escape(stage.explanation)}</div>
                  <div style="font-size:8.8pt; color:#64748b; margin-top:5px;">Artifact: {html.escape(stage.artifact)} | Evidence: {html.escape(stage.evidence_level)}</div>
                </div>
                """
            )
        return (
            '<div style="font-size:10pt; line-height:1.28;">'
            '<h2 style="color:#0f172a; margin:0 0 5px 0;">System Map: AI hardware skills</h2>'
            '<div style="color:#475569;">AutoEE calls specialized hardware skills, then turns their outputs into a reviewable design package.</div>'
            + "".join(rows)
            + "</div>"
        )

    def _package_items(self, state: DesignState) -> List[tuple[str, str, str]]:
        evaluation = safe_dict(safe_dict(state.deterministic_results.get("validation")).get("evaluation_summary"))
        missing = len(evaluation.get("missing_data", []) or []) if evaluation else None
        return [
            ("Specs", "spec_analyzer", "Electrical, thermal, transient, and acceptance targets"),
            ("BOM", "component_search", "Initial MOSFET, inductor, and capacitor selection"),
            ("Waveforms", "open_loop_sim", "Vout, inductor current, switch node, and load-step data"),
            ("Loss/Thermal", "loss_thermal", "Efficiency, loss distribution, and component temperature"),
            ("Control", "closed_loop_control", "Compensator seed and Bode stability summary"),
            ("PCB/3D Plan", "library_pcb_mechanical", "KiCad, footprint, FreeCAD, and manufacturing interface plan"),
            ("Risks", "validation", f"{missing} known gaps" if missing is not None else "Evaluation not run yet"),
            ("Next Actions", "report_generator", "Report package and signoff checklist"),
        ]

    def _package_html(self, state: DesignState, narrative: DemoNarrativeState) -> str:
        lines = []
        for label, module_id, description in self._package_items(state):
            done = module_id in state.deterministic_results
            status = "complete" if done else "waiting"
            icon = "OK" if done else "--"
            lines.append(
                f"""
                <div style="border:1px solid {'#10b981' if done else '#cbd5e1'}; border-radius:7px; padding:7px 9px; margin:5px 0; background:#ffffff;">
                  <div style="font-size:10.5pt; color:#0f172a; font-weight:700;">{icon} {html.escape(label)} {self._pill(status.title(), status)}</div>
                  <div style="font-size:8.8pt; color:#475569; margin-top:2px;">{html.escape(description)}</div>
                </div>
                """
            )
        ready = all(status == "complete" for status in narrative.stage_statuses.values())
        title = "Design Package Ready" if ready else "Design Package Building"
        summary = html.escape(narrative.final_summary)
        return (
            '<div style="font-size:10pt; line-height:1.28;">'
            f'<h2 style="color:#0f172a; margin:0 0 5px 0;">{title}</h2>'
            f'<div style="color:#334155; margin-bottom:6px;">{summary}</div>'
            + "".join(lines)
            + "</div>"
        )

    def _energy_html(self, state: DesignState) -> str:
        spec = state.spec
        loss = safe_dict(safe_dict(state.deterministic_results.get("loss_thermal")).get("loss_breakdown"))
        thermal = safe_dict(safe_dict(state.deterministic_results.get("loss_thermal")).get("thermal_result"))
        sim = safe_dict(safe_dict(state.deterministic_results.get("open_loop_sim")).get("simulation_result"))
        metrics = safe_dict(sim.get("metrics"))
        output_power = spec.output_voltage_v * spec.output_current_a
        total_loss = loss.get("total_loss_w")
        input_power = loss.get("input_power_w")
        efficiency = loss.get("efficiency_percent")
        max_temp = thermal.get("max_junction_temp_c")
        ripple = metrics.get("vout_ripple_mv_pp")
        transient = metrics.get("vout_transient_deviation_mv")
        values = [
            ("Output Power", fmt_num(output_power, " W"), "#0f172a"),
            ("Input Power", fmt_num(input_power, " W"), "#2563eb"),
            ("Lost as Heat", fmt_num(total_loss, " W"), "#b45309"),
            ("Efficiency", fmt_num(efficiency, "%"), "#047857"),
            ("Hot Spot", fmt_num(max_temp, " C"), temp_color(max_temp)),
            ("Ripple", fmt_num(ripple, " mVpp"), "#047857" if ripple is not None and float(ripple) <= spec.output_ripple_mv_pp else "#b45309"),
            ("Load Step", fmt_num(transient, " mV"), "#047857" if transient is not None and float(transient) <= spec.transient_deviation_mv else "#b45309"),
        ]
        cards = []
        for label, value, color in values:
            cards.append(
                f"""
                <td style="background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; padding:8px 10px;">
                  <div style="color:#64748b; font-size:8.6pt;">{html.escape(label)}</div>
                  <div style="color:{color}; font-size:13.5pt; font-weight:800;">{html.escape(value)}</div>
                </td>
                """
            )
        return (
            '<div style="font-size:10pt; line-height:1.25;">'
            '<h2 style="color:#0f172a; margin:0 0 6px 0;">Energy Story</h2>'
            '<table cellspacing="7" width="100%"><tr>'
            + "".join(cards[:4])
            + "</tr><tr>"
            + "".join(cards[4:])
            + "</tr></table>"
            '<div style="color:#64748b; font-size:8.8pt; margin-top:4px;">Plain English: output power is useful work; loss becomes heat; temperature decides whether the hardware can survive.</div>'
            "</div>"
        )

    def _evidence_html(self, narrative: DemoNarrativeState) -> str:
        rows = []
        for badge in narrative.badges:
            tone = "warn" if "not" in badge.signoff_status or "needs" in badge.signoff_status else "complete"
            rows.append(
                f"""
                <div style="display:block; border:1px solid #cbd5e1; border-radius:7px; background:#ffffff; padding:7px 9px; margin:5px 0;">
                  <div style="font-size:10.5pt; color:#0f172a; font-weight:700;">{html.escape(badge.label)} {self._pill(badge.signoff_status, tone)}</div>
                  <div style="font-size:8.8pt; color:#475569;">Source: {html.escape(badge.source_type)} | Confidence: {html.escape(badge.confidence)}</div>
                </div>
                """
            )
        return (
            '<div style="font-size:10pt; line-height:1.28;">'
            '<h2 style="color:#0f172a; margin:0 0 6px 0;">Evidence Badges</h2>'
            '<div style="color:#475569;">The demo is smooth, but AutoEE keeps source truth visible.</div>'
            + "".join(rows)
            + "</div>"
        )

    def update_from_state(self, state: DesignState, started_at: Optional[float] = None) -> None:
        narrative = build_demo_narrative_state(state, started_at)
        spec = state.spec
        done_count = sum(1 for value in narrative.stage_statuses.values() if value == "complete")
        ready = done_count == len(narrative.stages)
        status = "Design Package Ready" if ready else f"{done_count}/{len(narrative.stages)} skills complete"
        self.hero.setHtml(
            f"""
            <div style="font-size:10.5pt; line-height:1.30;">
              <h1 style="color:#0f172a; margin:0 0 4px 0;">From product requirement to verified hardware draft</h1>
              <div style="font-size:13pt; color:#047857; font-weight:800; margin-bottom:3px;">AutoEE is an AI Hardware Engineer</div>
              <div style="color:#334155;">
                Input: <b>{html.escape(INVESTOR_DEMO_PROMPT)}</b><br>
                Target: {spec.input_voltage_min_v:g}-{spec.input_voltage_max_v:g}V input to {spec.output_voltage_v:g}V/{spec.output_current_a:g}A output.
                Current demo state: {self._pill(status, 'complete' if ready else 'running')}
              </div>
              <div style="color:#64748b; font-size:9pt; margin-top:5px;">
                VC view: the main screen explains value; Engineering Console keeps the technical details one click away.
              </div>
            </div>
            """
        )
        self.stage_view.setHtml(self._stage_html(narrative))
        self.package_view.setHtml(self._package_html(state, narrative))
        self.energy_view.setHtml(self._energy_html(state))
        self.evidence_view.setHtml(self._evidence_html(narrative))


class DarkCanvas(FigureCanvasQTAgg):
    def __init__(self, fig: Figure):
        fig.patch.set_facecolor("#ffffff")
        super().__init__(fig)

    @staticmethod
    def style_axis(ax, title: str = "") -> None:
        ax.set_facecolor("#ffffff")
        ax.tick_params(colors="#334155", labelsize=9)
        for spine in ax.spines.values():
            spine.set_edgecolor("#cbd5e1")
        ax.grid(True, alpha=0.55, color="#e2e8f0")
        if title:
            ax.set_title(title, color="#0f172a", fontsize=11, pad=8)
        ax.xaxis.label.set_color("#334155")
        ax.yaxis.label.set_color("#334155")
        ax.xaxis.label.set_size(9.5)
        ax.yaxis.label.set_size(9.5)


class WaveformCanvas(DarkCanvas):
    def __init__(self, parent=None, mode: str = "overview"):
        self.mode = mode
        self.highlight = ""
        self.fig = Figure(figsize=(7.6, 5.4), dpi=100)
        self.ax_vout, self.ax_il, self.ax_sw, self.ax_load = self.fig.subplots(4, 1, sharex=True)
        super().__init__(self.fig)
        self.setParent(parent)
        self.draw_empty()

    def _layout(self) -> None:
        self.fig.subplots_adjust(left=0.085, right=0.985, bottom=0.10, top=0.91, hspace=0.20)

    def set_highlight(self, metric_key: str) -> None:
        self.highlight = metric_key

    def draw_empty(self) -> None:
        for ax in (self.ax_vout, self.ax_il, self.ax_sw, self.ax_load):
            ax.clear()
            self.style_axis(ax)
        title = "Transient Overview" if self.mode == "overview" else "Switching Zoom"
        self.ax_vout.set_title(title, color="#64748b", fontsize=10.5)
        self.ax_vout.set_ylabel("Vout (V)")
        self.ax_il.set_ylabel("IL (A)")
        self.ax_sw.set_ylabel("SW (V)")
        self.ax_load.set_ylabel("Iout (A)")
        self.ax_load.set_xlabel("Time")
        self.ax_vout.text(0.5, 0.5, "Run Open-loop Sim", transform=self.ax_vout.transAxes, ha="center", va="center", color="#64748b")
        self._layout()
        self.draw()

    @staticmethod
    def _event_time_us(sim: Dict[str, Any], event_name: str, default: float) -> float:
        for event in sim.get("events", []) or []:
            if isinstance(event, dict) and event.get("name") == event_name:
                try:
                    return float(event.get("time_us"))
                except (TypeError, ValueError):
                    return default
        return default

    def _slice_indices(self, time_us: List[float], sim: Dict[str, Any]) -> List[int]:
        if not time_us:
            return []
        if self.mode != "zoom":
            max_points = 1800
            if len(time_us) <= max_points:
                return list(range(len(time_us)))
            step = max(1, len(time_us) // max_points)
            return list(range(0, len(time_us), step))
        metrics = safe_dict(sim.get("metrics"))
        fsw = float(metrics.get("switching_frequency_hz") or 400_000.0)
        step_us = self._event_time_us(sim, "load_step", time_us[len(time_us) // 2])
        window_us = max(40.0, 20.0 / max(fsw, 1.0) * 1e6)
        start = step_us - window_us / 2.0
        stop = step_us + window_us / 2.0
        idxs = [idx for idx, value in enumerate(time_us) if start <= float(value) <= stop]
        return idxs or list(range(min(len(time_us), 200)))

    def update_from_state(self, state: DesignState) -> None:
        sim = safe_dict(safe_dict(state.deterministic_results.get("open_loop_sim")).get("simulation_result"))
        waves = safe_dict(sim.get("waveforms"))
        if not waves:
            self.draw_empty()
            return
        time_us = list(waves.get("time_us", []))
        vout = list(waves.get("vout_v", []))
        il = list(waves.get("il_a", []))
        switch = list(waves.get("switch_v", []))
        load_current = list(waves.get("load_current_a", []))
        duty_command = list(waves.get("duty_command", []))
        if not time_us or not vout or not il or not switch:
            self.draw_empty()
            return
        if not load_current:
            load_current = [state.spec.output_current_a for _ in time_us]
        if not duty_command:
            duty_command = [0.0 for _ in time_us]
        idxs = self._slice_indices([float(t) for t in time_us], sim)
        x_raw = [float(time_us[idx]) for idx in idxs]
        x_vals = [value / 1000.0 for value in x_raw] if self.mode == "overview" else x_raw
        x_label = "Time (ms)" if self.mode == "overview" else "Time (us)"
        vout_vals = [float(vout[idx]) for idx in idxs]
        il_vals = [float(il[idx]) for idx in idxs]
        sw_vals = [float(switch[idx]) for idx in idxs]
        load_vals = [float(load_current[idx]) for idx in idxs]
        duty_vals = [float(duty_command[idx]) for idx in idxs]
        spec = state.spec
        metrics = safe_dict(sim.get("metrics"))
        limits = safe_dict(sim.get("limit_bands"))
        upper_ripple = float(limits.get("ripple_upper_v", spec.output_voltage_v + spec.output_ripple_mv_pp / 2000.0))
        lower_ripple = float(limits.get("ripple_lower_v", spec.output_voltage_v - spec.output_ripple_mv_pp / 2000.0))
        upper_transient = float(limits.get("transient_upper_v", spec.output_voltage_v + spec.transient_deviation_mv / 1000.0))
        lower_transient = float(limits.get("transient_lower_v", spec.output_voltage_v - spec.transient_deviation_mv / 1000.0))
        upper_tol = float(limits.get("tolerance_upper_v", spec.output_voltage_v * (1 + spec.output_tolerance_percent / 100.0)))
        lower_tol = float(limits.get("tolerance_lower_v", spec.output_voltage_v * (1 - spec.output_tolerance_percent / 100.0)))
        il_sat = limits.get("il_saturation_placeholder_a")
        il_limit = limits.get("il_current_limit_placeholder_a")
        step_us = self._event_time_us(sim, "load_step", 1000.0)
        settling_end_us = float(limits.get("settling_end_us", step_us + spec.transient_settling_ms * 1000.0))
        step_x = step_us / 1000.0 if self.mode == "overview" else step_us
        settling_x = settling_end_us / 1000.0 if self.mode == "overview" else settling_end_us
        ripple_pass = metrics.get("vout_ripple_mv_pp") is not None and float(metrics["vout_ripple_mv_pp"]) <= spec.output_ripple_mv_pp
        transient_pass = metrics.get("vout_transient_deviation_mv") is not None and float(metrics["vout_transient_deviation_mv"]) <= spec.transient_deviation_mv
        status = "PASS" if ripple_pass and transient_pass else "CHECK"
        status_color = "#047857" if status == "PASS" else "#b45309"
        source_badge = str(sim.get("source_badge") or f"{sim.get('backend', 'missing')}: not signoff")

        self.ax_vout.clear()
        self.ax_il.clear()
        self.ax_sw.clear()
        self.ax_load.clear()
        for ax in (self.ax_vout, self.ax_il, self.ax_sw, self.ax_load):
            self.style_axis(ax)
            ax.axvline(step_x, color="#d97706", linestyle="--", linewidth=0.9, alpha=0.8)
        title = "Transient Overview" if self.mode == "overview" else "Switching Zoom Around Load Step"
        self.ax_vout.set_title(
            f"{title}  {status}  ripple {fmt_num(metrics.get('vout_ripple_mv_pp'), ' mVpp')}  "
            f"ILpk {fmt_num(metrics.get('inductor_peak_a'), ' A')}  source: {source_badge}",
            color=status_color,
            fontsize=11,
        )
        self.ax_vout.axhspan(lower_tol, upper_tol, color="#bfdbfe", alpha=0.35, label="Tolerance")
        self.ax_vout.axhspan(lower_transient, upper_transient, color="#bfdbfe", alpha=0.28, label="Transient limit")
        ripple_alpha = 0.26 if self.highlight == "ripple" else 0.14
        il_linewidth = 1.9 if self.highlight == "il" else 1.3
        self.ax_vout.axhspan(lower_ripple, upper_ripple, color="#6ee7b7", alpha=max(ripple_alpha, 0.18), label="Ripple band")
        self.ax_vout.axhline(spec.output_voltage_v, color="#64748b", linestyle=":", linewidth=1.0)
        self.ax_vout.plot(x_vals, vout_vals, color="#059669", linewidth=1.5, label="Vout")
        if vout_vals:
            peak_idx = max(range(len(vout_vals)), key=lambda idx: vout_vals[idx])
            valley_idx = min(range(len(vout_vals)), key=lambda idx: vout_vals[idx])
            self.ax_vout.scatter([x_vals[peak_idx]], [vout_vals[peak_idx]], color="#dc2626", s=20, zorder=5)
            self.ax_vout.scatter([x_vals[valley_idx]], [vout_vals[valley_idx]], color="#d97706", s=20, zorder=5)
        self.ax_vout.axvspan(step_x, settling_x, color="#fbbf24", alpha=0.18, label="Settling window")

        self.ax_il.plot(x_vals, il_vals, color="#2563eb", linewidth=il_linewidth, label="IL")
        self.ax_il.axhline(spec.output_current_a, color="#64748b", linestyle=":", linewidth=0.9, label="Full-load avg")
        if il_sat is not None:
            self.ax_il.axhline(float(il_sat), color="#dc2626", linestyle="--", linewidth=0.9, label="Sat placeholder")
        if il_limit is not None:
            self.ax_il.axhline(float(il_limit), color="#d97706", linestyle="--", linewidth=0.9, label="Current limit placeholder")
        if il_vals:
            peak_idx = max(range(len(il_vals)), key=lambda idx: il_vals[idx])
            valley_idx = min(range(len(il_vals)), key=lambda idx: il_vals[idx])
            self.ax_il.scatter([x_vals[peak_idx]], [il_vals[peak_idx]], color="#dc2626", s=18, zorder=5)
            self.ax_il.scatter([x_vals[valley_idx]], [il_vals[valley_idx]], color="#d97706", s=18, zorder=5)

        self.ax_sw.step(x_vals, sw_vals, where="post", color="#d97706", linewidth=1.1, label="SW")
        duty_scaled = [value * max(sw_vals or [1.0]) for value in duty_vals]
        self.ax_sw.plot(x_vals, duty_scaled, color="#64748b", linewidth=0.9, alpha=0.65, label="Duty command scaled")
        self.ax_load.step(x_vals, load_vals, where="post", color="#7c3aed", linewidth=1.4, label="Iout/load")

        self.ax_vout.set_ylabel("Vout (V)")
        self.ax_il.set_ylabel("IL (A)")
        self.ax_sw.set_ylabel("SW (V)")
        self.ax_load.set_ylabel("Iout (A)")
        self.ax_load.set_xlabel(x_label)
        for ax in (self.ax_vout, self.ax_il, self.ax_sw, self.ax_load):
            ax.legend(loc="upper right", facecolor="#ffffff", edgecolor="#cbd5e1", labelcolor="#0f172a", fontsize=7.2, framealpha=0.96)
        if x_vals:
            self.ax_load.set_xlim(min(x_vals), max(x_vals))
        self._layout()
        self.draw_idle()


class BodeCanvas(DarkCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(5.8, 4.2), dpi=100)
        self.ax_mag, self.ax_phase = self.fig.subplots(2, 1, sharex=True)
        super().__init__(self.fig)
        self.setParent(parent)
        self.draw_empty()

    def _layout(self) -> None:
        self.fig.subplots_adjust(left=0.13, right=0.985, bottom=0.12, top=0.90, hspace=0.16)

    def draw_empty(self) -> None:
        for ax in (self.ax_mag, self.ax_phase):
            ax.set_xscale("linear")
            ax.clear()
            self.style_axis(ax)
            ax.set_xscale("log")
            ax.set_xlim(100.0, 1_000_000.0)
        self.ax_mag.set_title("Loop Gain Bode", color="#64748b", fontsize=10.5)
        self.ax_mag.set_ylabel("Mag (dB)")
        self.ax_phase.set_ylabel("Phase (deg)")
        self.ax_phase.set_xlabel("Frequency")
        self.ax_mag.axhline(0.0, color="#64748b", linestyle=":", linewidth=1.0)
        self.ax_phase.axhline(-180.0, color="#64748b", linestyle=":", linewidth=1.0)
        self.ax_mag.text(0.5, 0.5, "Run Closed-loop Control", transform=self.ax_mag.transAxes, ha="center", va="center", color="#64748b")
        self._layout()
        self.draw()

    def update_from_state(self, state: DesignState) -> None:
        bode = safe_dict(safe_dict(state.deterministic_results.get("closed_loop_control")).get("bode_plot"))
        freq = list(bode.get("freq_hz", []))
        mag = list(bode.get("mag_db", []))
        phase = list(bode.get("phase_deg", []))
        if not freq or not mag or not phase:
            self.draw_empty()
            return
        metrics = safe_dict(bode.get("metrics"))
        crossover = metrics.get("crossover_hz")
        pm = metrics.get("phase_margin_deg")
        gm = metrics.get("gain_margin_db")
        self.ax_mag.set_xscale("linear")
        self.ax_mag.clear()
        self.ax_phase.set_xscale("linear")
        self.ax_phase.clear()
        for ax in (self.ax_mag, self.ax_phase):
            self.style_axis(ax)
            ax.set_xscale("log")
            ax.set_xlim(min(freq), max(freq))
        self.ax_mag.plot(freq, mag, color="#059669", linewidth=1.8)
        self.ax_phase.plot(freq, phase, color="#2563eb", linewidth=1.6)
        self.ax_mag.axhline(0.0, color="#64748b", linestyle=":", linewidth=1.0)
        self.ax_phase.axhline(-180.0, color="#64748b", linestyle=":", linewidth=1.0)
        if crossover:
            self.ax_mag.axvline(float(crossover), color="#d97706", linestyle="--", linewidth=1.0)
            self.ax_phase.axvline(float(crossover), color="#d97706", linestyle="--", linewidth=1.0)
        title = f"Loop Gain Bode  fc {fmt_hz(crossover)}  PM {fmt_num(pm, ' deg')}  GM {fmt_num(gm, ' dB')}"
        self.ax_mag.set_title(title, color="#0f172a", fontsize=10)
        self.ax_mag.set_ylabel("Mag (dB)")
        self.ax_phase.set_ylabel("Phase (deg)")
        self.ax_phase.set_xlabel("Frequency (Hz)")
        self._layout()
        self.draw_idle()


class LossThermalCanvas(DarkCanvas):
    GROUP_COLORS = {
        "MOSFET": "#93c5fd",
        "Inductor": "#60a5fa",
        "Capacitors": "#a78bfa",
        "PCB/PDN": "#34d399",
        "Other": "#fbbf24",
    }

    def __init__(self, parent=None):
        self.fig = Figure(figsize=(8.6, 5.4), dpi=100)
        self.ax_sweep = None
        self.ax_loss_sweep = None
        self.ax_pie_peak = None
        self.ax_pie_full = None
        self.ax_thermal = None
        super().__init__(self.fig)
        self.setParent(parent)
        self.draw_empty()

    def _setup_axes(self) -> None:
        self.fig.clear()
        self.fig.patch.set_facecolor("#ffffff")
        grid = self.fig.add_gridspec(4, 4, width_ratios=[1.18, 1.18, 1.0, 1.0], height_ratios=[0.95, 0.95, 0.85, 0.85])
        self.ax_sweep = self.fig.add_subplot(grid[0:2, :2])
        self.ax_loss_sweep = self.fig.add_subplot(grid[2:4, :2])
        self.ax_pie_peak = self.fig.add_subplot(grid[0, 2])
        self.ax_pie_full = self.fig.add_subplot(grid[0, 3])
        self.ax_thermal = self.fig.add_subplot(grid[1:, 2:])
        self.fig.subplots_adjust(left=0.075, right=0.985, bottom=0.15, top=0.90, wspace=0.46, hspace=0.78)

    def draw_empty(self) -> None:
        self._setup_axes()
        self.style_axis(self.ax_sweep, "Loss vs Output Current")
        self.ax_sweep.set_xlabel("Output Current (A)")
        self.ax_sweep.set_ylabel("Efficiency (%)")
        self.ax_sweep.text(
            0.5,
            0.5,
            "Run Loss + Thermal",
            transform=self.ax_sweep.transAxes,
            ha="center",
            va="center",
            color="#707076",
            fontsize=13,
        )
        self.style_axis(self.ax_loss_sweep, "Loss Stack at Nominal Vin")
        self.ax_loss_sweep.set_xlabel("Output Current (A)")
        self.ax_loss_sweep.set_ylabel("Loss (W)")
        for ax, title in ((self.ax_pie_peak, "Peak Efficiency"), (self.ax_pie_full, "Full Power")):
            ax.set_facecolor("#ffffff")
            ax.set_title(title, color="#64748b", fontsize=10)
            ax.set_xticks([])
            ax.set_yticks([])
        self.ax_thermal.set_facecolor("#ffffff")
        self.ax_thermal.set_axis_off()
        self.ax_thermal.set_title("Thermal Temperature", color="#64748b", fontsize=10)
        self.draw()

    @staticmethod
    def _loss_scale(key: str, current_ratio: float, vin_ratio: float) -> float:
        current_ratio = max(0.0, current_ratio)
        if key in {"gate_drive"}:
            return 1.0
        if "coss" in key:
            return vin_ratio * vin_ratio
        if "switching" in key or "body_diode" in key or "reverse_recovery" in key:
            return current_ratio * vin_ratio
        if "core" in key:
            return 0.45 + 0.55 * (current_ratio ** 1.45)
        return current_ratio * current_ratio

    @classmethod
    def _scaled_items(cls, items: Dict[str, Any], current_a: float, full_current_a: float, vin_v: float, vin_nom_v: float) -> Dict[str, float]:
        current_ratio = current_a / max(full_current_a, 1e-9)
        vin_ratio = vin_v / max(vin_nom_v, 1e-9)
        scaled = {}
        for key, value in items.items():
            try:
                base = float(value)
            except (TypeError, ValueError):
                continue
            scaled[key] = max(0.0, base * cls._loss_scale(str(key), current_ratio, vin_ratio))
        return scaled

    @classmethod
    def _group_losses(cls, items: Dict[str, float]) -> Dict[str, float]:
        grouped = {name: 0.0 for name in cls.GROUP_COLORS}
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

    @staticmethod
    def _efficiency(vout_v: float, current_a: float, total_loss_w: float) -> float:
        output_power = max(0.0, vout_v * current_a)
        if output_power <= 0.0:
            return 0.0
        return output_power / (output_power + total_loss_w) * 100.0

    def _style_secondary_axis(self, ax) -> None:
        ax.tick_params(colors="#334155", labelsize=9)
        ax.yaxis.label.set_color("#334155")
        ax.yaxis.label.set_size(9.5)
        for spine in ax.spines.values():
            spine.set_edgecolor("#cbd5e1")

    def _draw_loss_sweep(self, state: DesignState, items: Dict[str, Any]) -> Dict[str, Any]:
        spec = state.spec
        full_current = max(0.05, float(spec.output_current_a))
        start_current = min(full_current, max(0.10, full_current * 0.10))
        currents = [start_current + (full_current - start_current) * idx / 44.0 for idx in range(45)]
        vin_candidates = [
            float(spec.input_voltage_min_v),
            float(spec.input_voltage_nominal_v),
            float(spec.input_voltage_max_v),
        ]
        vin_values: List[float] = []
        for vin in vin_candidates:
            if all(abs(vin - existing) > 0.01 for existing in vin_values):
                vin_values.append(vin)
        line_colors = ["#059669", "#2563eb", "#d97706"]
        nominal_vin = float(spec.input_voltage_nominal_v)

        self.style_axis(self.ax_sweep, "Efficiency Curves")
        self.style_axis(self.ax_loss_sweep, "Loss Breakdown at Nominal Vin")
        self.ax_sweep.set_xlabel("")
        self.ax_sweep.set_ylabel("Efficiency (%)")
        self.ax_sweep.axhline(float(spec.target_efficiency_percent), color="#059669", linestyle=":", linewidth=1.2, alpha=0.9, label="Efficiency target")
        peak_record = {"eff": -1.0, "current": full_current, "items": {}, "loss": 0.0}

        for idx, vin in enumerate(vin_values):
            efficiencies = []
            for current in currents:
                point_items = self._scaled_items(items, current, full_current, vin, nominal_vin)
                total_loss = sum(point_items.values())
                eff = self._efficiency(float(spec.output_voltage_v), current, total_loss)
                efficiencies.append(eff)
                if abs(vin - nominal_vin) < 0.01 and eff > peak_record["eff"]:
                    peak_record = {"eff": eff, "current": current, "items": point_items, "loss": total_loss}
            color = line_colors[idx % len(line_colors)]
            self.ax_sweep.plot(currents, efficiencies, color=color, linewidth=2.0, label=f"{vin:g}V efficiency")

        nominal_group_series = {name: [] for name in self.GROUP_COLORS}
        total_losses = []
        for current in currents:
            point_items = self._scaled_items(items, current, full_current, nominal_vin, nominal_vin)
            grouped = self._group_losses(point_items)
            for name in self.GROUP_COLORS:
                nominal_group_series[name].append(grouped[name])
            total_losses.append(sum(point_items.values()))

        stack_values = [nominal_group_series[name] for name in self.GROUP_COLORS]
        self.ax_loss_sweep.stackplot(
            currents,
            stack_values,
            labels=[f"{name} loss" for name in self.GROUP_COLORS],
            colors=[self.GROUP_COLORS[name] for name in self.GROUP_COLORS],
            alpha=0.50,
        )
        self.ax_loss_sweep.plot(currents, total_losses, color="#111827", linewidth=1.9, label="Total loss")
        self.ax_loss_sweep.axhline(float(spec.max_total_loss_w), color="#dc2626", linestyle=":", linewidth=1.2, alpha=0.9, label="Loss target")
        self.ax_loss_sweep.set_xlabel("Output Current (A)")
        self.ax_loss_sweep.set_ylabel("Loss (W)")
        self.ax_sweep.set_ylim(max(65.0, min(88.0, min(self.ax_sweep.get_ylim()))), 100.5)
        self.ax_loss_sweep.set_ylim(0.0, max(max(total_losses) * 1.25, float(spec.max_total_loss_w) * 1.15, 0.5))
        self.ax_sweep.legend(
            loc="lower right",
            facecolor="#ffffff",
            edgecolor="#cbd5e1",
            labelcolor="#0f172a",
            fontsize=7.4,
            framealpha=0.96,
        )
        self.ax_loss_sweep.legend(
            loc="upper left",
            bbox_to_anchor=(0.0, -0.18),
            ncol=3,
            facecolor="#ffffff",
            edgecolor="#cbd5e1",
            labelcolor="#0f172a",
            fontsize=6.8,
            framealpha=0.96,
        )
        source = "First-order estimate; solid lines = efficiency, filled area below = watts lost as heat."
        self.ax_sweep.text(
            0.02,
            0.05,
            source,
            transform=self.ax_sweep.transAxes,
            color="#92400e",
            fontsize=7.5,
            va="bottom",
            ha="left",
            bbox={"facecolor": "#fffbeb", "edgecolor": "#f59e0b", "alpha": 0.96, "pad": 3},
        )
        full_items = self._scaled_items(items, full_current, full_current, nominal_vin, nominal_vin)
        if not peak_record["items"]:
            peak_record = {"eff": 0.0, "current": full_current, "items": full_items, "loss": sum(full_items.values())}
        return {"peak": peak_record, "full": {"current": full_current, "items": full_items, "loss": sum(full_items.values())}}

    def _draw_pie(self, ax, grouped: Dict[str, float], title: str, subtitle: str) -> None:
        ax.clear()
        ax.set_facecolor("#ffffff")
        values = [value for value in grouped.values() if value > 1e-5]
        labels = [name for name, value in grouped.items() if value > 1e-5]
        colors = [self.GROUP_COLORS[name] for name in labels]
        if not values:
            ax.text(0.5, 0.5, "No loss data", transform=ax.transAxes, ha="center", va="center", color="#64748b")
            return
        wedges, _texts, autotexts = ax.pie(
            values,
            labels=None,
            colors=colors,
            autopct=lambda pct: f"{pct:.0f}%" if pct >= 7.0 else "",
            pctdistance=0.68,
            startangle=90,
            textprops={"color": "#0f172a", "fontsize": 7.2},
            wedgeprops={"linewidth": 0.7, "edgecolor": "#ffffff"},
        )
        for text in autotexts:
            text.set_color("#0f172a")
            text.set_fontweight("bold")
            text.set_fontsize(7.0)
        legend_labels = [f"{label} {value:.2f}W" for label, value in zip(labels, values)]
        ax.text(
            0.5,
            -0.16,
            " | ".join(legend_labels),
            transform=ax.transAxes,
            ha="center",
            va="top",
            color="#334155",
            fontsize=6.0,
            wrap=True,
        )
        ax.set_title(f"{title}\n{subtitle}", color="#0f172a", fontsize=8.5, pad=6)
        ax.axis("equal")

    def _draw_thermal_cards(self, thermal: Dict[str, Any]) -> None:
        self.ax_thermal.clear()
        self.ax_thermal.set_facecolor("#ffffff")
        self.ax_thermal.set_axis_off()
        self.ax_thermal.set_title("Thermal Readout", color="#0f172a", fontsize=10, pad=8)
        temps = safe_dict(thermal.get("component_temps_c"))
        if not temps:
            self.ax_thermal.text(0.5, 0.5, "No thermal estimate yet", transform=self.ax_thermal.transAxes, ha="center", va="center", color="#64748b")
            return
        preferred = [
            ("high_side_mosfet_junction", "High-side MOSFET"),
            ("low_side_mosfet_junction", "Low-side MOSFET"),
            ("inductor_hotspot", "Inductor Hotspot"),
            ("automotive_85c_high_side_estimate", "85C Ambient Warning"),
        ]
        rows = [(key, label, temps[key]) for key, label in preferred if key in temps]
        if not rows:
            rows = [(key, key.replace("_", " ").title(), value) for key, value in list(temps.items())[:4]]
        positions = [(0.03, 0.56), (0.52, 0.56), (0.03, 0.14), (0.52, 0.14)]
        for idx, (_key, label, value) in enumerate(rows[:4]):
            try:
                temp_value = float(value)
            except (TypeError, ValueError):
                continue
            x, y = positions[idx]
            color = temp_color(temp_value)
            self.ax_thermal.add_patch(
                Rectangle(
                    (x, y),
                    0.43,
                    0.30,
                    transform=self.ax_thermal.transAxes,
                    facecolor="#ffffff",
                    edgecolor=color,
                    linewidth=2.0,
                    alpha=0.98,
                )
            )
            self.ax_thermal.text(x + 0.03, y + 0.205, label, transform=self.ax_thermal.transAxes, color="#334155", fontsize=8.2, weight="bold")
            self.ax_thermal.text(
                x + 0.03,
                y + 0.065,
                f"{temp_value:.1f} C",
                transform=self.ax_thermal.transAxes,
                color=color,
                fontsize=16,
                weight="bold",
            )
        self.ax_thermal.text(
            0.03,
            0.01,
            "Color scale: green <85C | yellow 85-105C | orange 105-125C | red >=125C\n"
            "Thermal model: Tj = Ta + P x RthetaJA_eff. Board and airflow dependent.",
            transform=self.ax_thermal.transAxes,
            color="#475569",
            fontsize=7.2,
            bbox={"facecolor": "#f8fafc", "edgecolor": "#cbd5e1", "alpha": 1.0, "pad": 4},
        )

    def update_from_state(self, state: DesignState) -> None:
        loss = safe_dict(safe_dict(state.deterministic_results.get("loss_thermal")).get("loss_breakdown"))
        thermal = safe_dict(safe_dict(state.deterministic_results.get("loss_thermal")).get("thermal_result"))
        items = safe_dict(loss.get("items_w"))
        temps = safe_dict(thermal.get("component_temps_c"))
        if not items and not temps:
            self.draw_empty()
            return
        self._setup_axes()
        if items:
            sweep_points = self._draw_loss_sweep(state, items)
            peak_grouped = self._group_losses(sweep_points["peak"]["items"])
            full_grouped = self._group_losses(sweep_points["full"]["items"])
            peak_subtitle = (
                f"{sweep_points['peak']['current']:.2f}A, "
                f"{sweep_points['peak']['eff']:.1f}% eff"
            )
            full_eff = self._efficiency(state.spec.output_voltage_v, sweep_points["full"]["current"], sweep_points["full"]["loss"])
            full_subtitle = f"{sweep_points['full']['current']:.2f}A, {full_eff:.1f}% eff"
            self._draw_pie(self.ax_pie_peak, peak_grouped, "Peak Efficiency Loss", peak_subtitle)
            self._draw_pie(self.ax_pie_full, full_grouped, "Full-Power Loss", full_subtitle)
        else:
            self.style_axis(self.ax_sweep, "Loss vs Output Current")
            self.ax_sweep.text(0.5, 0.5, "No loss breakdown yet", transform=self.ax_sweep.transAxes, ha="center", va="center", color="#707076")
            self.style_axis(self.ax_loss_sweep, "Loss Stack")
        self._draw_thermal_cards(thermal)
        self.draw_idle()


class AgentWorker(QtCore.QObject):
    assistant_message = QtCore.pyqtSignal(str)
    log_message = QtCore.pyqtSignal(str)
    progress_changed = QtCore.pyqtSignal(str, int, int)
    state_changed = QtCore.pyqtSignal()
    error_occurred = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal(str)

    def __init__(
        self,
        agent: AutoEEAgent,
        mode: str,
        prompt: str,
        module_ids: Optional[List[str]] = None,
        output_dir: Optional[Path] = None,
        min_module_seconds: float = 0.0,
    ):
        super().__init__()
        self.agent = agent
        self.mode = mode
        self.prompt = prompt
        self.module_ids = module_ids or []
        self.output_dir = output_dir
        self.min_module_seconds = max(0.0, float(min_module_seconds))
        self._stop = False

    def stop(self) -> None:
        self._stop = True
        self.agent.stop()

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            if self.mode == "chat":
                self._run_chat()
            else:
                self._run_modules()
        except Exception as exc:
            self.error_occurred.emit(str(exc))
        finally:
            self.finished.emit(self.mode)

    def _run_chat(self) -> None:
        self.log_message.emit("Model backend is preparing an answer from current DesignState.")
        text = self._ask_model(
            self.prompt,
            fallback=local_design_summary(self.agent.state),
            intent="Answer the user's engineering question using the current AutoEE design state.",
        )
        self.assistant_message.emit(text)

    def _run_modules(self) -> None:
        total = len(self.module_ids)
        self.agent.stop_requested = False
        self.agent.state.workflow_status = "running"
        self.agent.state.record_event("agent", "running", f"Agent command received: {self.prompt[:180]}")
        self.state_changed.emit()
        self.assistant_message.emit(self._opening_run_message(self.module_ids))
        for idx, module_id in enumerate(self.module_ids, start=1):
            if self._stop or self.agent.stop_requested:
                self.agent.state.record_event(module_id, "stopped", "Stopped before module execution.")
                self.progress_changed.emit(module_id, idx - 1, total)
                self.state_changed.emit()
                break
            self.progress_changed.emit(module_id, idx - 1, total)
            self.log_message.emit(f"Running {module_id}...")
            self.agent.state.record_event(module_id, "running", "Module is running.")
            self.state_changed.emit()
            started = time.monotonic()
            result = self.agent.run_skill(module_id, output_dir=self.output_dir)
            remaining = self.min_module_seconds - (time.monotonic() - started)
            while remaining > 0 and not self._stop and not self.agent.stop_requested:
                time.sleep(min(0.10, remaining))
                remaining = self.min_module_seconds - (time.monotonic() - started)
            if self._stop or self.agent.stop_requested:
                self.agent.state.record_event(module_id, "stopped", "Stopped after module calculation before completion display.")
                self.progress_changed.emit(module_id, idx - 1, total)
                self.state_changed.emit()
                break
            self.log_message.emit(f"Done {module_id}: {result.summary}")
            narration = INVESTOR_NARRATION.get(module_id)
            if narration:
                self.assistant_message.emit(narration)
            self.progress_changed.emit(module_id, idx, total)
            self.state_changed.emit()
            time.sleep(0.08)
        if self._stop or self.agent.stop_requested:
            self.agent.state.workflow_status = "stopped"
            self.assistant_message.emit("Stopped. Current partial design state is preserved, so you can edit specs or resume from any skill.")
            self.state_changed.emit()
            return
        self.agent.state.workflow_status = "complete" if self.module_ids and self.module_ids[-1] == self.agent.skills[-1].module_id else "partial"
        final = self._ask_model(
            "Summarize the AutoEE run, call out numeric results, risks, next actions, and which data is mock/synthetic.",
            fallback=local_design_summary(self.agent.state),
            intent="Produce the final engineering agent response after executing AutoEE skills.",
        )
        self.assistant_message.emit(final)
        self.state_changed.emit()

    def _opening_run_message(self, module_ids: List[str]) -> str:
        names = [self.agent.skill_map[module_id].title for module_id in module_ids if module_id in self.agent.skill_map]
        return "I will run these AutoEE skills:\n- " + "\n- ".join(names)

    def _ask_model(self, prompt: str, fallback: str, intent: str) -> str:
        if self.agent.model_manager is None:
            return fallback
        try:
            response = self.agent.model_manager.chat(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are AutoEE's AI design agent. Use deterministic module results as facts. "
                            "Do not overwrite engineering calculations. Be concise, practical, and explicit about mock data."
                        ),
                    },
                    {"role": "user", "content": f"{intent}\n\nUser request:\n{self.prompt}\n\nTask:\n{prompt}"},
                ],
                context=self.agent.state.model_context_payload(),
                timeout=25.0,
            )
        except Exception as exc:
            return f"{fallback}\n\nModel backend error: {exc}"
        if response.unavailable or not response.text.strip():
            return f"{fallback}\n\nAI backend unavailable: {response.text.strip() or 'no response'}"
        return response.text.strip()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoEE Agent Workbench")
        self.resize(1440, 900)
        self.model_manager = ModelManager(ModelBackendSettings.load())
        self.agent = AutoEEAgent(DesignState(), self.model_manager)
        self.spec_widgets: Dict[str, QtWidgets.QDoubleSpinBox] = {}
        self._worker: Optional[AgentWorker] = None
        self._thread: Optional[QtCore.QThread] = None
        self._run_output_dir: Optional[Path] = None
        self._demo_started_at: Optional[float] = None

        self._build_ui()
        self._apply_dark_theme()
        self._append_chat(
            "assistant",
            "I am AutoEE Agent. For a VC demo, click Run Demo and I will turn one product request into a reviewable hardware design package.",
        )
        self.render_state()

    @property
    def design_state(self) -> DesignState:
        return self.agent.state

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter)
        splitter.addWidget(self._build_agent_panel())
        splitter.addWidget(self._build_workbench_panel())
        splitter.setSizes([420, 1020])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self._build_menus()
        self.statusBar().showMessage(self.status_text())

    def _build_agent_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        panel.setObjectName("AgentPanel")
        panel.setMinimumWidth(360)
        panel.setMaximumWidth(520)
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 8, 10)
        layout.setSpacing(8)

        header = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("AutoEE Agent")
        title.setObjectName("AppTitle")
        self.provider_label = QtWidgets.QLabel(self.provider_text())
        self.provider_label.setObjectName("ProviderPill")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.provider_label)
        layout.addLayout(header)

        self.chat_view = QtWidgets.QTextBrowser()
        self.chat_view.setObjectName("ChatView")
        self.chat_view.setOpenExternalLinks(True)
        layout.addWidget(self.chat_view, 1)

        self.chat_input = QtWidgets.QPlainTextEdit()
        self.chat_input.setObjectName("ChatInput")
        self.chat_input.setPlaceholderText("Ask AutoEE to run a workflow, explain risks, or show Bode/control...")
        self.chat_input.setMaximumHeight(92)
        layout.addWidget(self.chat_input)

        send_row = QtWidgets.QHBoxLayout()
        self.btn_send = QtWidgets.QPushButton("Send")
        self.btn_send.setObjectName("PrimaryButton")
        self.btn_send.clicked.connect(self.on_send_message)
        self.btn_run_all = QtWidgets.QPushButton("Run Demo")
        self.btn_run_all.clicked.connect(self.on_run_investor_demo)
        self.btn_stop = QtWidgets.QPushButton("Stop")
        self.btn_stop.clicked.connect(self.on_stop_clicked)
        self.btn_stop.setEnabled(False)
        self.btn_reset_all = QtWidgets.QPushButton("Reset All")
        self.btn_reset_all.clicked.connect(self.on_reset_all)
        send_row.addWidget(self.btn_send)
        send_row.addWidget(self.btn_run_all)
        send_row.addWidget(self.btn_stop)
        send_row.addWidget(self.btn_reset_all)
        layout.addLayout(send_row)

        self.run_progress = QtWidgets.QProgressBar()
        self.run_progress.setRange(0, len(self.agent.skills))
        self.run_progress.setValue(0)
        self.run_progress.setFormat("Ready")
        layout.addWidget(self.run_progress)

        narration_box = QtWidgets.QGroupBox("Narration")
        narration_layout = QtWidgets.QVBoxLayout(narration_box)
        self.narration_view = QtWidgets.QTextBrowser()
        self.narration_view.setObjectName("NarrationView")
        self.narration_view.setReadOnly(True)
        self.narration_view.setMaximumHeight(118)
        narration_layout.addWidget(self.narration_view)
        layout.addWidget(narration_box)

        plan_box = QtWidgets.QGroupBox("Agent Plan")
        plan_layout = QtWidgets.QVBoxLayout(plan_box)
        self.agent_plan = QtWidgets.QPlainTextEdit()
        self.agent_plan.setReadOnly(True)
        self.agent_plan.setMaximumHeight(96)
        plan_layout.addWidget(self.agent_plan)
        layout.addWidget(plan_box)

        skill_box = QtWidgets.QGroupBox("Skill Timeline")
        skill_layout = QtWidgets.QVBoxLayout(skill_box)
        self.skill_table = QtWidgets.QTableWidget(len(self.agent.skills), 3)
        self.skill_table.setHorizontalHeaderLabels(["Skill", "Status", "Module"])
        self.skill_table.verticalHeader().setVisible(False)
        self.skill_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.skill_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.skill_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.skill_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.skill_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.skill_table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.skill_table.setMinimumHeight(235)
        self.skill_table.cellClicked.connect(lambda *_: self.render_selected_result())
        skill_layout.addWidget(self.skill_table)
        skill_buttons = QtWidgets.QHBoxLayout()
        self.btn_run_selected = QtWidgets.QPushButton("Run Selected")
        self.btn_run_selected.clicked.connect(self.on_run_selected_clicked)
        self.btn_reset_selected = QtWidgets.QPushButton("Reset Selected")
        self.btn_reset_selected.clicked.connect(self.on_reset_selected_clicked)
        skill_buttons.addWidget(self.btn_run_selected)
        skill_buttons.addWidget(self.btn_reset_selected)
        skill_layout.addLayout(skill_buttons)
        layout.addWidget(skill_box)

        brief_box = QtWidgets.QGroupBox("Design Brief")
        brief_layout = QtWidgets.QVBoxLayout(brief_box)
        self.name_edit = QtWidgets.QLineEdit(self.agent.state.spec.name)
        brief_layout.addWidget(self.name_edit)
        form = QtWidgets.QGridLayout()
        form.setHorizontalSpacing(7)
        form.setVerticalSpacing(5)
        spec = self.agent.state.spec
        for idx, (attr, label, unit, minimum, maximum, decimals, step) in enumerate(SPEC_FIELDS):
            row = idx // 2
            col = (idx % 2) * 3
            lab = QtWidgets.QLabel(label)
            spin = QtWidgets.QDoubleSpinBox()
            spin.setRange(minimum, maximum)
            spin.setDecimals(decimals)
            spin.setSingleStep(step)
            spin.setValue(float(getattr(spec, attr)))
            spin.setSuffix(f" {unit}")
            self.spec_widgets[attr] = spin
            form.addWidget(lab, row, col)
            form.addWidget(spin, row, col + 1)
        brief_layout.addLayout(form)
        self.btn_apply_specs = QtWidgets.QPushButton("Apply Specs")
        self.btn_apply_specs.clicked.connect(self.apply_specs)
        brief_layout.addWidget(self.btn_apply_specs)
        layout.addWidget(brief_box)

        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Return"), self, activated=self.on_send_message)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Enter"), self, activated=self.on_send_message)
        return panel

    def _build_workbench_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        panel.setObjectName("WorkbenchPanel")
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(8, 10, 10, 10)
        layout.setSpacing(8)

        self.workspace_tabs = QtWidgets.QTabWidget()
        self.workspace_tabs.setObjectName("WorkspaceTabs")
        layout.addWidget(self.workspace_tabs, 1)

        self.investor_demo = InvestorDemoPanel()
        self.investor_demo.btn_run_demo.clicked.connect(self.on_run_investor_demo)
        self.investor_demo.btn_reset_demo.clicked.connect(self.on_reset_demo)
        self.investor_demo.btn_export_snapshot.clicked.connect(self.export_investor_snapshot)
        self.workspace_tabs.addTab(self.investor_demo, "Investor Demo")

        engineering = QtWidgets.QWidget()
        engineering_layout = QtWidgets.QVBoxLayout(engineering)
        engineering_layout.setContentsMargins(0, 0, 0, 0)
        engineering_layout.setSpacing(8)

        tiles = QtWidgets.QHBoxLayout()
        self.tile_status = StatTile("Health", "Idle", metric_key="evaluation")
        self.tile_eff = StatTile("Efficiency", "-", metric_key="loss")
        self.tile_loss = StatTile("Total Loss", "-", metric_key="loss")
        self.tile_temp = StatTile("Max Temp", "-", metric_key="thermal")
        self.tile_ripple = StatTile("Vout Ripple", "-", metric_key="ripple")
        self.tile_il_peak = StatTile("IL Peak", "-", metric_key="il")
        self.tile_pm = StatTile("Phase Margin", "-", metric_key="bode")
        self.tile_missing = StatTile("Missing Data", "-", metric_key="evaluation")
        for tile in [
            self.tile_status,
            self.tile_eff,
            self.tile_loss,
            self.tile_temp,
            self.tile_ripple,
            self.tile_il_peak,
            self.tile_pm,
            self.tile_missing,
        ]:
            tile.clicked.connect(self.on_metric_tile_clicked)
            tiles.addWidget(tile)
        engineering_layout.addLayout(tiles)

        vertical = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        vertical.setChildrenCollapsible(False)
        engineering_layout.addWidget(vertical, 1)

        self.plot_tabs = QtWidgets.QTabWidget()
        self.plot_tabs.setObjectName("PlotTabs")
        self.design_overview = DesignOverviewPanel()
        self.design_rationale = DesignRationalePanel()
        self.waveform_canvas = WaveformCanvas(mode="overview")
        self.switching_canvas = WaveformCanvas(mode="zoom")
        self.bode_canvas = BodeCanvas()
        self.loss_canvas = LossThermalCanvas()
        self.plot_tabs.addTab(self.design_overview, "Design Overview")
        self.plot_tabs.addTab(self.design_rationale, "Design Rationale")
        self.plot_tabs.addTab(self.waveform_canvas, "Waveform Lab")
        self.plot_tabs.addTab(self.switching_canvas, "Switching Zoom")
        self.plot_tabs.addTab(self.bode_canvas, "Bode")
        self.plot_tabs.addTab(self.loss_canvas, "Loss + Thermal")
        vertical.addWidget(self.plot_tabs)

        self.bottom_tabs = QtWidgets.QTabWidget()
        self.bottom_tabs.setObjectName("BottomTabs")
        self.event_log = QtWidgets.QPlainTextEdit()
        self.event_log.setReadOnly(True)
        self.selected_result = QtWidgets.QPlainTextEdit()
        self.selected_result.setReadOnly(True)
        self.evaluation_summary = QtWidgets.QPlainTextEdit()
        self.evaluation_summary.setReadOnly(True)
        self.state_json = QtWidgets.QPlainTextEdit()
        self.state_json.setReadOnly(True)
        self.bottom_tabs.addTab(self.event_log, "Progress")
        self.bottom_tabs.addTab(self.evaluation_summary, "Evaluation")
        self.bottom_tabs.addTab(self.selected_result, "Selected Skill")
        self.bottom_tabs.addTab(self.state_json, "State JSON")
        vertical.addWidget(self.bottom_tabs)
        vertical.setSizes([610, 250])
        self.workspace_tabs.addTab(engineering, "Engineering Console")
        self.workspace_tabs.setCurrentWidget(self.investor_demo)
        return panel

    def _build_menus(self) -> None:
        run_investor = QtWidgets.QAction("Run 3-Min Investor Demo", self)
        run_investor.triggered.connect(self.on_run_investor_demo)
        reset_investor = QtWidgets.QAction("Reset Investor Demo", self)
        reset_investor.triggered.connect(self.on_reset_demo)
        export_snapshot = QtWidgets.QAction("Export Investor Snapshot", self)
        export_snapshot.triggered.connect(self.export_investor_snapshot)
        run_full = QtWidgets.QAction("Run Full Demo", self)
        run_full.triggered.connect(self.on_run_all_clicked)
        run_control = QtWidgets.QAction("Run Control + Bode", self)
        run_control.triggered.connect(lambda: self.start_worker("run", "Run control and Bode workflow", modules_until(self.agent, "closed_loop_control")))
        settings_action = QtWidgets.QAction("Model Backend", self)
        settings_action.triggered.connect(self.open_model_backend_settings)
        export_report = QtWidgets.QAction("Export Report", self)
        export_report.triggered.connect(lambda: self.start_worker("run", "Export report", modules_until(self.agent, "report_generator")))

        workflow_menu = self.menuBar().addMenu("Workflow")
        workflow_menu.addAction(run_investor)
        workflow_menu.addAction(reset_investor)
        workflow_menu.addAction(export_snapshot)
        workflow_menu.addSeparator()
        workflow_menu.addAction(run_full)
        workflow_menu.addAction(run_control)
        workflow_menu.addAction(export_report)
        settings_menu = self.menuBar().addMenu("Settings")
        settings_menu.addAction(settings_action)

    def _apply_dark_theme(self) -> None:
        self.setStyleSheet(
            """
            * { font-family: "Segoe UI", "Inter", sans-serif; font-size: 9.4pt; }
            QMainWindow, QWidget { background: #f8fafc; color: #0f172a; }
            QWidget#AgentPanel { background: #ffffff; border-right: 1px solid #cbd5e1; }
            QWidget#WorkbenchPanel { background: #f8fafc; }
            QLabel { color: #334155; }
            QLabel#AppTitle { color: #0f172a; font-size: 17px; font-weight: 700; }
            QLabel#ProviderPill {
                color: #047857; background: #ecfdf5; border: 1px solid #10b981;
                border-radius: 4px; padding: 4px 7px; font-size: 8.8pt;
            }
            QGroupBox {
                border: 1px solid #cbd5e1; border-radius: 5px; margin-top: 8px;
                padding-top: 10px; color: #475569; font-weight: 600; background: #ffffff;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
            QTextBrowser#ChatView, QPlainTextEdit, QTextEdit {
                background: #ffffff; color: #0f172a; border: 1px solid #cbd5e1;
                border-radius: 5px; padding: 7px; font-size: 9.2pt;
            }
            QTextBrowser#DesignOverview {
                background: #ffffff; color: #0f172a; border: 1px solid #cbd5e1;
                border-radius: 6px; padding: 9px; font-size: 9.4pt;
            }
            QTextBrowser#DesignRationale {
                background: #ffffff; color: #0f172a; border: 1px solid #cbd5e1;
                border-radius: 6px; padding: 10px; font-size: 9.3pt;
            }
            QTextBrowser#InvestorHero, QTextBrowser#InvestorStage, QTextBrowser#InvestorPackage,
            QTextBrowser#InvestorEnergy, QTextBrowser#InvestorEvidence, QTextBrowser#NarrationView {
                background: #ffffff; color: #0f172a; border: 1px solid #cbd5e1;
                border-radius: 7px; padding: 8px; font-size: 9.4pt;
            }
            QTextBrowser#InvestorHero {
                background: #f0fdfa; border: 1px solid #10b981;
            }
            QLabel#DemoPrompt {
                color: #064e3b; background: #ecfdf5; border: 1px solid #10b981;
                border-radius: 6px; padding: 6px 9px; font-size: 9.3pt; font-weight: 700;
            }
            QPlainTextEdit#ChatInput {
                background: #ffffff; color: #0f172a; border: 1px solid #cbd5e1;
                border-radius: 6px; padding: 8px; font-size: 9.4pt;
            }
            QPlainTextEdit#ChatInput:focus, QLineEdit:focus, QDoubleSpinBox:focus {
                border: 1px solid #10b981;
            }
            QPushButton {
                background: #ffffff; color: #0f172a; border: 1px solid #cbd5e1;
                border-radius: 5px; padding: 6px 10px; font-weight: 600; font-size: 9.2pt;
            }
            QPushButton:hover { background: #f1f5f9; }
            QPushButton:pressed { background: #e2e8f0; }
            QPushButton:disabled { background: #f1f5f9; color: #94a3b8; border-color: #e2e8f0; }
            QPushButton#PrimaryButton {
                background: #047857; border: 1px solid #047857; color: #ffffff;
            }
            QPushButton#PrimaryButton:hover { background: #059669; }
            QLineEdit, QDoubleSpinBox, QComboBox {
                background: #ffffff; color: #0f172a; border: 1px solid #cbd5e1;
                border-radius: 4px; padding: 5px 6px; font-size: 9.1pt;
            }
            QTabWidget::pane { border: 1px solid #cbd5e1; top: -1px; background: #ffffff; }
            QTabBar::tab {
                background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1;
                padding: 7px 12px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px;
            }
            QTabBar::tab:selected { background: #ffffff; color: #0f172a; border-top: 2px solid #10b981; }
            QTableWidget {
                background: #ffffff; color: #0f172a; gridline-color: #e2e8f0;
                selection-background-color: #dbeafe; alternate-background-color: #f8fafc;
            }
            QHeaderView::section {
                background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; padding: 5px 6px;
            }
            QProgressBar {
                background: #ffffff; color: #0f172a; border: 1px solid #cbd5e1;
                border-radius: 4px; text-align: center; min-height: 20px;
            }
            QProgressBar::chunk { background: #10b981; border-radius: 3px; }
            QFrame#StatTile {
                background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px;
            }
            QFrame#StatTile[tone="pass"] { border-color: #10b981; }
            QFrame#StatTile[tone="warn"] { border-color: #f59e0b; }
            QFrame#StatTile[tone="fail"] { border-color: #ef4444; }
            QLabel#StatLabel { color: #64748b; font-size: 8.4pt; }
            QLabel#StatValue { color: #0f172a; font-size: 11.8pt; font-weight: 700; }
            QStatusBar { color: #64748b; }
            QSplitter::handle { background: #e2e8f0; }
            QScrollBar:vertical { background: #f8fafc; width: 10px; border: none; }
            QScrollBar::handle:vertical { background: #cbd5e1; border-radius: 5px; min-height: 28px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            """
        )

    def provider_text(self) -> str:
        return f"{self.model_manager.settings.default_provider}"

    def status_text(self) -> str:
        return f"Default model provider: {self.model_manager.settings.default_provider}"

    def selected_module_id(self) -> str:
        row = self.skill_table.currentRow()
        if row < 0:
            return self.agent.skills[0].module_id
        item = self.skill_table.item(row, 2)
        return item.text() if item else self.agent.skills[0].module_id

    def render_state(self) -> None:
        self._render_skill_table()
        self._render_status_tiles()
        self._render_progress()
        self._render_agent_plan()
        self._render_narration()
        self._render_evaluation_summary()
        self.render_selected_result()
        self.state_json.setPlainText(json.dumps(self.design_state.to_dict(), indent=2, sort_keys=True))
        self.investor_demo.update_from_state(self.design_state, self._demo_started_at)
        self.design_overview.update_from_state(self.design_state)
        self.design_rationale.update_from_state(self.design_state)
        self.waveform_canvas.update_from_state(self.design_state)
        self.switching_canvas.update_from_state(self.design_state)
        self.bode_canvas.update_from_state(self.design_state)
        self.loss_canvas.update_from_state(self.design_state)
        self.statusBar().showMessage(self.status_text())

    def _render_skill_table(self) -> None:
        for row, skill in enumerate(self.agent.skills):
            title = QtWidgets.QTableWidgetItem(skill.title)
            status = self.design_state.module_status.get(skill.module_id, "idle")
            status_item = QtWidgets.QTableWidgetItem(status)
            module = QtWidgets.QTableWidgetItem(skill.module_id)
            tone = {
                "complete": QtGui.QColor("#047857"),
                "running": QtGui.QColor("#b45309"),
                "error": QtGui.QColor("#dc2626"),
                "stopped": QtGui.QColor("#c2410c"),
            }.get(status, QtGui.QColor("#64748b"))
            status_item.setForeground(tone)
            self.skill_table.setItem(row, 0, title)
            self.skill_table.setItem(row, 1, status_item)
            self.skill_table.setItem(row, 2, module)
        if self.skill_table.currentRow() < 0:
            self.skill_table.setCurrentCell(0, 0)

    def _render_status_tiles(self) -> None:
        status = self.design_state.workflow_status
        loss = safe_dict(safe_dict(self.design_state.deterministic_results.get("loss_thermal")).get("loss_breakdown"))
        thermal = safe_dict(safe_dict(self.design_state.deterministic_results.get("loss_thermal")).get("thermal_result"))
        control = safe_dict(safe_dict(self.design_state.deterministic_results.get("closed_loop_control")).get("control_result"))
        sim = safe_dict(safe_dict(self.design_state.deterministic_results.get("open_loop_sim")).get("simulation_result"))
        sim_metrics = safe_dict(sim.get("metrics"))
        limits = safe_dict(sim.get("limit_bands"))
        evaluation = safe_dict(safe_dict(self.design_state.deterministic_results.get("validation")).get("evaluation_summary"))
        eval_status = evaluation.get("overall_status")
        health_value = str(eval_status or status or "idle").title()
        health_tone = {
            "pass": "pass",
            "partial": "warn",
            "missing": "fail",
            "blocked_requires_approval": "warn",
            "complete": "warn",
        }.get(str(eval_status or status), "neutral")
        self.tile_status.set_value(health_value, health_tone)
        efficiency = loss.get("efficiency_percent")
        total_loss = loss.get("total_loss_w")
        max_temp = thermal.get("max_junction_temp_c")
        self.tile_eff.set_value(fmt_num(efficiency, "%"), "pass" if efficiency and float(efficiency) >= self.design_state.spec.target_efficiency_percent else "warn" if efficiency else "neutral")
        self.tile_loss.set_value(fmt_num(total_loss, " W"), "pass" if total_loss and float(total_loss) <= self.design_state.spec.max_total_loss_w else "warn" if total_loss else "neutral")
        self.tile_temp.set_value(
            fmt_num(max_temp, " C"),
            "fail" if max_temp and float(max_temp) >= 125.0 else "warn" if max_temp and float(max_temp) >= 85.0 else "pass" if max_temp else "neutral",
        )
        ripple = sim_metrics.get("vout_ripple_mv_pp")
        self.tile_ripple.set_value(
            fmt_num(ripple, " mVpp"),
            "pass" if ripple is not None and float(ripple) <= self.design_state.spec.output_ripple_mv_pp else "warn" if ripple is not None else "neutral",
        )
        il_peak = sim_metrics.get("inductor_peak_a")
        il_sat = limits.get("il_saturation_placeholder_a")
        il_tone = "neutral"
        if il_peak is not None and il_sat is not None:
            il_tone = "pass" if float(il_peak) <= float(il_sat) else "fail"
        elif il_peak is not None:
            il_tone = "warn"
        self.tile_il_peak.set_value(fmt_num(il_peak, " A"), il_tone)
        pm = control.get("phase_margin_deg")
        self.tile_pm.set_value(
            fmt_num(pm, " deg"),
            "pass" if pm is not None and float(pm) >= 45.0 else "warn" if pm is not None else "neutral",
        )
        missing_count = len(evaluation.get("missing_data", []) or []) if evaluation else None
        self.tile_missing.set_value(
            str(missing_count) if missing_count is not None else "-",
            "pass" if missing_count == 0 else "warn" if missing_count is not None and missing_count < 10 else "fail" if missing_count is not None else "neutral",
        )

    def _render_agent_plan(self) -> None:
        lines = ["Agent execution plan:"]
        for idx, skill in enumerate(self.agent.skills, start=1):
            status = self.design_state.module_status.get(skill.module_id, "idle")
            lines.append(f"{idx}. {skill.title}: {status}")
        evaluation = safe_dict(safe_dict(self.design_state.deterministic_results.get("validation")).get("evaluation_summary"))
        next_actions = list(evaluation.get("recommended_next_actions", []) or [])
        if next_actions:
            lines.extend(["", "Next action:", next_actions[0]])
        else:
            lines.extend(["", "Next action:", "Run Full Demo to generate design evidence."])
        self.agent_plan.setPlainText("\n".join(lines))

    def _render_narration(self) -> None:
        narrative = build_demo_narrative_state(self.design_state, self._demo_started_at)
        current_stage = next((stage for stage in narrative.stages if stage.id == narrative.current_stage_id), narrative.stages[-1])
        status = narrative.stage_statuses.get(current_stage.id, "waiting")
        if all(value == "complete" for value in narrative.stage_statuses.values()):
            title = "Founder talk track: Design Package Ready"
            body = (
                "AutoEE has generated a reviewable hardware draft: specs, BOM, loss and thermal model, "
                "waveforms, control seed, PCB/3D plan, evaluation, and report. The key point is not just automation; "
                "it also records which evidence is synthetic or still needs signoff."
            )
        elif status == "waiting":
            title = f"Founder talk track: {current_stage.title}"
            body = (
                f"Start with the customer request, then let AutoEE show how an AI hardware engineer calls the next skill: "
                f"{current_stage.explanation}"
            )
        else:
            title = f"Founder talk track: {current_stage.title}"
            body = f"Explain this as a hardware skill in progress: {current_stage.explanation}"
        self.narration_view.setHtml(
            f"""
            <div style="font-size:9.4pt; line-height:1.32;">
              <div style="color:#047857; font-weight:800; margin-bottom:4px;">{html.escape(title)}</div>
              <div style="color:#0f172a;">{html.escape(body)}</div>
            </div>
            """
        )

    def _render_progress(self) -> None:
        lines = [
            f"[{event.timestamp}] {event.module_id}: {event.status} - {event.message}"
            for event in self.design_state.progress_events[-120:]
        ]
        self.event_log.setPlainText("\n".join(lines))
        self.event_log.moveCursor(QtGui.QTextCursor.End)

    def _render_evaluation_summary(self) -> None:
        evaluation = safe_dict(safe_dict(self.design_state.deterministic_results.get("validation")).get("evaluation_summary"))
        if not evaluation:
            self.evaluation_summary.setPlainText("No evaluation has run yet.")
            return
        lines = [
            f"Overall status: {evaluation.get('overall_status', '-')}",
            "",
            "Categories:",
        ]
        categories = safe_dict(evaluation.get("categories"))
        lines.extend(f"- {key}: {value}" for key, value in sorted(categories.items()))
        lines.extend(["", "Missing data:"])
        missing = list(evaluation.get("missing_data", []) or [])
        lines.extend(f"- {item}" for item in missing[:40])
        if len(missing) > 40:
            lines.append(f"- ... {len(missing) - 40} more")
        lines.extend(["", "Risks:"])
        lines.extend(f"- {item}" for item in list(evaluation.get("risks", []) or [])[:30])
        lines.extend(["", "Recommended next actions:"])
        lines.extend(f"- {item}" for item in evaluation.get("recommended_next_actions", []) or [])
        self.evaluation_summary.setPlainText("\n".join(lines))

    def on_metric_tile_clicked(self, metric_key: str) -> None:
        self.workspace_tabs.setCurrentIndex(1)
        if metric_key in {"ripple", "il"}:
            self.waveform_canvas.set_highlight(metric_key)
            self.switching_canvas.set_highlight(metric_key)
            self.plot_tabs.setCurrentWidget(self.waveform_canvas)
        elif metric_key in {"bode", "pm"}:
            self.plot_tabs.setCurrentWidget(self.bode_canvas)
        elif metric_key in {"loss", "thermal"}:
            self.plot_tabs.setCurrentWidget(self.loss_canvas)
        elif metric_key == "evaluation":
            self.bottom_tabs.setCurrentWidget(self.evaluation_summary)
        self.render_state()

    def render_selected_result(self) -> None:
        module_id = self.selected_module_id()
        skill = self.agent.skill_map.get(module_id)
        result = self.design_state.deterministic_results.get(module_id)
        lines = []
        if skill:
            lines.extend([f"{skill.title} ({skill.module_id})", skill.description, ""])
        note = self.design_state.ai_notes.get(module_id)
        if note:
            lines.extend(["Summary:", note, ""])
        if result is None:
            lines.append("No result yet.")
        else:
            lines.extend(["Result JSON:", json.dumps(result, indent=2, sort_keys=True)])
        self.selected_result.setPlainText("\n".join(lines))

    def _append_chat(self, role: str, text: str) -> None:
        color = "#047857" if role == "assistant" else "#2563eb" if role == "user" else "#64748b"
        label = "AutoEE" if role == "assistant" else "You" if role == "user" else "System"
        body = html.escape(text).replace("\n", "<br>")
        self.chat_view.append(
            f'<div style="margin:8px 0;">'
            f'<span style="color:{color}; font-weight:700;">{label}</span>'
            f'<div style="color:#0f172a; line-height:1.35; margin-top:3px;">{body}</div>'
            f"</div>"
        )
        self.chat_view.moveCursor(QtGui.QTextCursor.End)

    def _append_log(self, text: str) -> None:
        self.design_state.record_event("ui", "log", text)
        self._render_progress()

    def open_model_backend_settings(self) -> None:
        dialog = ModelBackendDialog(self.model_manager, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.provider_label.setText(self.provider_text())
            self.statusBar().showMessage(self.status_text())

    def apply_specs(self) -> None:
        spec = self.agent.state.spec
        spec.name = self.name_edit.text().strip() or spec.name
        for attr, widget in self.spec_widgets.items():
            setattr(spec, attr, float(widget.value()))
        self.agent.state.clear_from([skill.module_id for skill in self.agent.skills])
        self.agent.state.record_event("spec_editor", "edited", "Specs updated from GUI; downstream module results cleared.")
        self._append_chat("assistant", "Specs applied. Downstream results were cleared so the next run uses the edited design brief.")
        self.render_state()

    def on_send_message(self) -> None:
        prompt = self.chat_input.toPlainText().strip()
        if not prompt:
            return
        self.chat_input.clear()
        self._append_chat("user", prompt)
        lower = prompt.lower()
        if any(term in lower or term in prompt for term in STOP_TERMS):
            self.on_stop_clicked()
            return
        if any(term in lower or term in prompt for term in RESET_TERMS):
            self.on_reset_all()
            return
        module_ids = modules_for_prompt(self.agent, prompt)
        if module_ids:
            self.start_worker("run", prompt, module_ids)
        else:
            self.start_worker("chat", prompt, None)

    def on_run_investor_demo(self) -> None:
        self.workspace_tabs.setCurrentWidget(self.investor_demo)
        current_spec = self.agent.state.spec
        self.agent.state = DesignState(spec=current_spec)
        self._demo_started_at = time.monotonic()
        self._append_chat("user", INVESTOR_DEMO_PROMPT)
        self._append_chat(
            "assistant",
            "I reset the previous demo results and will run the demo: product requirement, specs, parts, loss/thermal, waveforms, control, validation, and design package.",
        )
        self.start_worker("run", INVESTOR_DEMO_PROMPT, [skill.module_id for skill in self.agent.skills], min_module_seconds=0.5)

    def on_run_all_clicked(self) -> None:
        self._append_chat("user", "Run the full AutoEE Buck charger workflow.")
        self.start_worker("run", "Run the full AutoEE Buck charger workflow.", [skill.module_id for skill in self.agent.skills])

    def on_run_selected_clicked(self) -> None:
        module_id = self.selected_module_id()
        prompt = f"Run selected skill: {module_id}"
        self._append_chat("user", prompt)
        self.start_worker("run", prompt, modules_until(self.agent, module_id))

    def on_reset_selected_clicked(self) -> None:
        module_id = self.selected_module_id()
        self.agent.reset_module(module_id)
        self._append_chat("assistant", f"Reset {module_id}.")
        self.render_state()

    def on_reset_demo(self) -> None:
        if self._thread is not None:
            QtWidgets.QMessageBox.information(self, "AutoEE Agent", "Stop the current run before resetting the investor demo.")
            return
        current_spec = self.agent.state.spec
        self.agent.state = DesignState(spec=current_spec)
        self._demo_started_at = None
        self.chat_view.clear()
        self._append_chat(
            "assistant",
            "Investor demo reset. Start from the default product request, then run the demo to build the design package live.",
        )
        self.run_progress.setRange(0, len(self.agent.skills))
        self.run_progress.setValue(0)
        self.run_progress.setFormat("Ready")
        self.workspace_tabs.setCurrentWidget(self.investor_demo)
        self.render_state()

    def on_reset_all(self) -> None:
        current_spec = self.agent.state.spec
        self.agent.state = DesignState(spec=current_spec)
        self._demo_started_at = None
        self._append_chat("assistant", "Reset workflow state and kept the current specs.")
        self.render_state()

    def investor_snapshot_markdown(self) -> str:
        narrative = build_demo_narrative_state(self.design_state, self._demo_started_at)
        spec = self.design_state.spec
        lines = [
            "# AutoEE Investor Snapshot",
            "",
            "## Demo Thesis",
            "AutoEE is an AI Hardware Engineer that turns a product requirement into a reviewable hardware design package.",
            "",
            "## Product Request",
            f"`{INVESTOR_DEMO_PROMPT}`",
            "",
            "## Target Design",
            f"- Input: {spec.input_voltage_min_v:g}-{spec.input_voltage_max_v:g} V",
            f"- Output: {spec.output_voltage_v:g} V / {spec.output_current_a:g} A",
            f"- Ripple target: <= {spec.output_ripple_mv_pp:g} mVpp",
            f"- Transient target: <= {spec.transient_deviation_mv:g} mV",
            f"- Efficiency target: >= {spec.target_efficiency_percent:g} %",
            "",
            "## Generated In This Run",
        ]
        for stage in narrative.stages:
            status = narrative.stage_statuses.get(stage.id, "waiting")
            lines.append(f"- {stage.title}: {status} - {stage.artifact} ({stage.evidence_level})")
        lines.extend(["", "## Key Results", build_investor_summary(self.design_state), "", "## Evidence Badges"])
        for badge in narrative.badges:
            lines.append(f"- {badge.label}: source={badge.source_type}; confidence={badge.confidence}; status={badge.signoff_status}")
        evaluation = safe_dict(safe_dict(self.design_state.deterministic_results.get("validation")).get("evaluation_summary"))
        if evaluation:
            lines.extend(["", "## Risks And Next Actions"])
            for risk in list(evaluation.get("risks", []) or [])[:8]:
                lines.append(f"- Risk: {risk}")
            for action in list(evaluation.get("recommended_next_actions", []) or [])[:5]:
                lines.append(f"- Next: {action}")
        lines.extend(
            [
                "",
                "## Honesty Note",
                "This investor demo uses mock catalog, synthetic waveform, analytical control, and placeholder PCB/3D data where real tools are not configured. These outputs are demo-backed estimates, not signoff-ready evidence.",
            ]
        )
        return "\n".join(lines)

    def export_investor_snapshot(self, output_dir: Optional[Path] = None) -> Path:
        root = Path(output_dir) if output_dir else Path("results") / "investor_snapshots"
        root.mkdir(parents=True, exist_ok=True)
        path = root / f"investor_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        path.write_text(self.investor_snapshot_markdown(), encoding="utf-8")
        self._append_chat("assistant", f"Exported investor snapshot: {path}")
        self.statusBar().showMessage(f"Investor snapshot exported: {path}")
        return path

    def on_stop_clicked(self) -> None:
        if self._worker is not None:
            self._worker.stop()
        else:
            self.agent.stop()
            self.render_state()
        self.statusBar().showMessage("Stop requested.")

    def start_worker(self, mode: str, prompt: str, module_ids: Optional[List[str]], min_module_seconds: float = 0.0) -> None:
        if self._thread is not None:
            QtWidgets.QMessageBox.information(self, "AutoEE Agent", "A run is already in progress.")
            return
        output_dir = None
        if mode == "run":
            output_dir = Path("results") / "gui_runs" / datetime.now().strftime("%Y%m%d_%H%M%S")
        worker = AgentWorker(self.agent, mode, prompt, module_ids=module_ids, output_dir=output_dir, min_module_seconds=min_module_seconds)
        thread = QtCore.QThread(self)
        self._worker = worker
        self._thread = thread
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.assistant_message.connect(lambda text: self._append_chat("assistant", text))
        worker.log_message.connect(self._append_log)
        worker.progress_changed.connect(self.on_worker_progress)
        worker.state_changed.connect(self.render_state)
        worker.error_occurred.connect(self.on_worker_error)
        worker.finished.connect(lambda _mode, t=thread: t.quit())
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(self.on_worker_finished)
        thread.finished.connect(thread.deleteLater)
        self._set_running(True)
        thread.start()

    def on_worker_progress(self, module_id: str, current: int, total: int) -> None:
        self.run_progress.setRange(0, max(total, 1))
        self.run_progress.setValue(current)
        self.run_progress.setFormat(f"{module_id}  {current}/{total}")

    def on_worker_error(self, message: str) -> None:
        self.agent.state.record_event("agent", "error", message)
        self._append_chat("assistant", f"Run failed: {message}")
        self.render_state()

    def on_worker_finished(self, mode: str) -> None:
        self._set_running(False)
        if mode == "run":
            total = max(self.run_progress.maximum(), 1)
            self.run_progress.setValue(total)
            self.run_progress.setFormat("Finished")
            if self.workspace_tabs.currentWidget() == self.investor_demo:
                self._append_chat("assistant", "Design Package Ready: the investor demo now has a full reviewable draft, with mock/synthetic evidence clearly labeled.")
        else:
            self.run_progress.setFormat("Ready")
        self.render_state()
        self._worker = None
        self._thread = None

    def _set_running(self, running: bool) -> None:
        self.btn_send.setEnabled(not running)
        self.btn_run_all.setEnabled(not running)
        self.btn_run_selected.setEnabled(not running)
        self.btn_reset_selected.setEnabled(not running)
        self.btn_reset_all.setEnabled(not running)
        self.btn_apply_specs.setEnabled(not running)
        self.investor_demo.btn_run_demo.setEnabled(not running)
        self.investor_demo.btn_reset_demo.setEnabled(not running)
        self.investor_demo.btn_export_snapshot.setEnabled(not running)
        self.btn_stop.setEnabled(running)
        self.chat_input.setReadOnly(running)
        self.statusBar().showMessage("Running..." if running else self.status_text())


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch the AutoEE demo GUI.")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Validate settings can load and print the default provider without opening a window.",
    )
    return parser


def main(argv=None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.smoke:
        settings = ModelBackendSettings.load()
        print(f"AutoEE GUI smoke OK. Default provider: {settings.default_provider}")
        return 0

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
