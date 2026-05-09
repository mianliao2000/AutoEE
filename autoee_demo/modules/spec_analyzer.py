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
                },
            ),
        )

