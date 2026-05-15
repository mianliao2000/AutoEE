from __future__ import annotations

from pathlib import Path
from typing import Optional

from autoee_demo.core.state import DesignCandidate, DesignState
from autoee_demo.model_backend import ModelManager

from .base import AutoEESkill, SkillRunResult


class SpecAnalyzer(AutoEESkill):
    module_id = "spec_analyzer"
    title = "Specs"
    description = "Build constraint matrix and default Buck charger acceptance criteria."

    def run(
        self,
        state: DesignState,
        model_manager: Optional[ModelManager] = None,
        output_dir: Optional[Path] = None,
    ) -> SkillRunResult:
        spec = state.spec
        fsw = 400_000.0
        inductor_uh = 10.0
        output_cap_uf = 94.0
        input_cap_uf = 44.0
        duty_nominal = spec.output_voltage_v / spec.input_voltage_nominal_v
        candidate = DesignCandidate(
            topology="synchronous buck",
            switching_frequency_hz=fsw,
            inductor_uh=inductor_uh,
            output_cap_uf=output_cap_uf,
            input_cap_uf=input_cap_uf,
            duty_nominal=duty_nominal,
            notes=[
                "Scenario is a 15W vehicle/industrial USB-C charger, not a random lab value.",
                "400 kHz keeps magnetics practical while preserving room for efficiency.",
                "10 uH yields manageable ripple at 36 V input for a 5 V / 3 A rail.",
            ],
        )

        constraints = {
            "source_reference": [
                "TI PMP40286: automotive USB-C 5V/3A + USB-A charger, >91% at 12Vin full load",
                "TI PMP40543: automotive 15W USB-C + 12W USB-A charger, 93.2% at 27W output",
            ],
            "electrical": {
                "vin_range_v": [spec.input_voltage_min_v, spec.input_voltage_max_v],
                "vout_v": spec.output_voltage_v,
                "iout_a": spec.output_current_a,
                "vout_tolerance_percent": spec.output_tolerance_percent,
                "steady_state_ripple_mv_pp_max": spec.output_ripple_mv_pp,
                "load_transient_a": f"0.3A to {spec.output_current_a}A",
                "transient_deviation_mv_max": spec.transient_deviation_mv,
                "settling_ms_max": spec.transient_settling_ms,
            },
            "thermal": {
                "ambient_demo_c": spec.ambient_temp_c,
                "ambient_automotive_warning_c": spec.automotive_warning_ambient_c,
                "max_total_loss_w": spec.max_total_loss_w,
            },
            "acceptance": {
                "efficiency_percent_min": spec.target_efficiency_percent,
                "must_run_without_external_tools": True,
                "human_signoff_required": True,
            },
        }
        execution_plan = [
            {
                "step": "Parts",
                "goal": "Select a reviewable first-pass BOM for the buck power stage.",
                "inputs": ["constraint matrix", "topology seed", "voltage/current margins"],
                "outputs": ["MOSFETs", "inductor", "input/output capacitors", "price and stock table"],
                "sourceType": "fake_digikey_mouser",
                "realCapabilityStatus": "not_connected",
                "nextIntegration": "Replace mock distributor records with DigiKey and Mouser API responses.",
            },
            {
                "step": "Analysis",
                "goal": "Estimate power loss, efficiency, and component temperature risk from selected parts.",
                "inputs": ["selected BOM", "datasheet-like parameters", "electrical specs"],
                "outputs": ["loss breakdown", "thermal cards", "efficiency estimate"],
                "sourceType": "first_order_demo_model",
                "realCapabilityStatus": "demo_estimate_not_signoff",
                "nextIntegration": "Calibrate loss and thermal equations against real datasheets and measured board data.",
            },
            {
                "step": "Simulation",
                "goal": "Generate waveform evidence for output ripple, inductor current, and load-step response.",
                "inputs": ["power-stage candidate", "loss model", "load transient spec"],
                "outputs": ["Vout waveform", "inductor current", "switch node", "load current trace"],
                "sourceType": "synthetic_waveform",
                "realCapabilityStatus": "not_connected",
                "nextIntegration": "Replace synthetic waveform generation with PLECS or LTspice export.",
            },
            {
                "step": "Control",
                "goal": "Create a first closed-loop compensation seed and stability target.",
                "inputs": ["plant estimate", "BOM parasitics", "simulation metrics"],
                "outputs": ["control mode", "compensator type", "PID/Type-3 seed", "Bode metrics"],
                "sourceType": "analytical_synthetic_loop_gain",
                "realCapabilityStatus": "demo_estimate_not_signoff",
                "nextIntegration": "Replace analytical seed with simulation-backed or bench auto-tuning.",
            },
            {
                "step": "PCB",
                "goal": "Plan library generation, schematic creation, placement/routing, Gerber export, and manufacturing handoff.",
                "inputs": ["selected parts", "datasheet package data", "layout constraints"],
                "outputs": ["symbol/footprint plan", "schematic plan", "layout plan", "Gerber/JLCPCB handoff plan"],
                "sourceType": "fake_kicad_jlcpcb_pipeline",
                "realCapabilityStatus": "not_connected",
                "nextIntegration": "Connect KiCad automation, DRC/ERC, Gerber export, and JLCPCB API handoff.",
            },
            {
                "step": "Test",
                "goal": "Define post-prototype firmware download, tuning, data capture, and report generation.",
                "inputs": ["assembled prototype", "firmware seed", "bench instruments"],
                "outputs": ["firmware flash log", "tuning record", "efficiency sweep", "test report"],
                "sourceType": "fake_lab_workflow",
                "realCapabilityStatus": "not_connected",
                "nextIntegration": "Connect firmware build/flash tooling and lab instrument automation.",
            },
        ]
        summary = (
            "Prepared 15W USB-C Buck charger constraints and selected a 400 kHz, "
            "10 uH, 94 uF starting point."
        )
        return self.complete(
            state,
            SkillRunResult(
                module_id=self.module_id,
                title=self.title,
                summary=summary,
                data={
                    "constraint_matrix": constraints,
                    "selected_candidate": candidate.to_dict(),
                    "available_tools": [
                        "mock DigiKey",
                        "synthetic sim",
                        "control synthesis",
                        "Maxwell placeholder",
                        "KiCad/FreeCAD placeholder",
                    ],
                    "execution_plan": execution_plan,
                    "sourceType": "deterministic_demo_planner",
                    "realCapabilityStatus": "demo_data_not_signoff",
                },
            ),
        )
