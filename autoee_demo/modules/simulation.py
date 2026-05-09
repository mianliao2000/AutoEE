from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

from autoee_demo.core.state import DesignState, SimulationResult
from autoee_demo.model_backend import ModelManager

from .base import AutoEESkill, SkillRunResult, require_result


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


class CircuitSimulationBackend(AutoEESkill):
    module_id = "open_loop_sim"
    title = "Open-loop Sim"
    description = "Synthetic PLECS/LTspice-compatible waveform source for the Buck charger demo."

    def run(
        self,
        state: DesignState,
        model_manager: Optional[ModelManager] = None,
        output_dir: Optional[Path] = None,
    ) -> SkillRunResult:
        spec_result = require_result(state, "spec_analyzer")
        loss_result = require_result(state, "loss_thermal")
        spec = state.spec
        candidate = spec_result["selected_candidate"]
        fsw = float(candidate["switching_frequency_hz"])
        inductance_h = float(candidate["inductor_uh"]) * 1e-6
        output_cap_f = float(candidate["output_cap_uf"]) * 1e-6
        duty = float(loss_result["derived"]["duty_nominal"])
        samples = 8000
        duration_s = 2.0e-3
        step_time_s = 1.0e-3
        low_load_a = max(0.0, spec.output_current_a - spec.transient_step_a)
        vin = spec.input_voltage_nominal_v
        vout_target = spec.output_voltage_v
        cap_esr_ohm = 0.002
        cap_voltage = vout_target
        current_loop_tau_s = 8.0e-6
        voltage_restore_tau_s = 180.0e-6
        dt_s = duration_s / (samples - 1)
        time_us = []
        vout = []
        il = []
        switch = []
        load_current = []
        duty_command = []
        for idx in range(samples):
            t = idx / (samples - 1) * duration_s
            carrier = (t * fsw) % 1.0
            stepped = t >= step_time_s
            post_step_s = max(0.0, t - step_time_s)
            iout = low_load_a if not stepped else spec.output_current_a
            current_envelope = math.exp(-post_step_s / current_loop_tau_s) if stepped else 1.0
            inductor_average = low_load_a if not stepped else spec.output_current_a - spec.transient_step_a * current_envelope
            duty_boost = 0.22 * math.exp(-post_step_s / 35e-6) if stepped else 0.0
            duty_inst = _clamp(duty + duty_boost, 0.05, 0.88)
            ripple_a = (vin - vout_target) * duty_inst / (inductance_h * fsw)
            if carrier < duty_inst:
                tri = -0.5 + carrier / max(duty_inst, 1e-6)
            else:
                tri = 0.5 - (carrier - duty_inst) / max(1.0 - duty_inst, 1e-6)
            il_raw = inductor_average + ripple_a * tri
            il_value = max(0.0, il_raw) if inductor_average < ripple_a / 2.0 else il_raw
            cap_voltage += ((il_value - iout) / output_cap_f - (cap_voltage - vout_target) / voltage_restore_tau_s) * dt_s
            vout_value = cap_voltage + cap_esr_ohm * (il_value - iout)
            time_us.append(round(t * 1e6, 3))
            vout.append(round(vout_value, 5))
            il.append(round(il_value, 5))
            switch.append(round(vin if carrier < duty_inst else 0.0, 4))
            load_current.append(round(iout, 5))
            duty_command.append(round(duty_inst, 5))
        steady_vout = vout[-min(400, len(vout)) :]
        post_step_vout = vout[int(samples * 0.5) :]
        ripple_a_nominal = (vin - vout_target) * duty / (inductance_h * fsw)
        limit_bands = {
            "nominal_v": spec.output_voltage_v,
            "tolerance_upper_v": spec.output_voltage_v * (1.0 + spec.output_tolerance_percent / 100.0),
            "tolerance_lower_v": spec.output_voltage_v * (1.0 - spec.output_tolerance_percent / 100.0),
            "ripple_upper_v": spec.output_voltage_v + spec.output_ripple_mv_pp / 2000.0,
            "ripple_lower_v": spec.output_voltage_v - spec.output_ripple_mv_pp / 2000.0,
            "transient_upper_v": spec.output_voltage_v + spec.transient_deviation_mv / 1000.0,
            "transient_lower_v": spec.output_voltage_v - spec.transient_deviation_mv / 1000.0,
            "settling_end_us": round((step_time_s + spec.transient_settling_ms / 1000.0) * 1e6, 3),
            "il_saturation_placeholder_a": round(max(spec.output_current_a + ripple_a_nominal, spec.output_current_a * 1.8), 3),
            "il_current_limit_placeholder_a": round(max(spec.output_current_a + ripple_a_nominal * 0.75, spec.output_current_a * 1.5), 3),
        }
        events = [
            {
                "name": "load_step",
                "time_us": round(step_time_s * 1e6, 3),
                "from_a": round(low_load_a, 3),
                "to_a": round(spec.output_current_a, 3),
                "description": "Synthetic load step used to exercise Vout transient response.",
            },
            {
                "name": "settling_limit",
                "time_us": limit_bands["settling_end_us"],
                "description": "Spec settling deadline after the load step.",
            },
        ]
        metrics = {
            "vout_ripple_mv_pp": round((max(steady_vout) - min(steady_vout)) * 1000.0, 3),
            "vout_min_after_step_v": round(min(post_step_vout), 4),
            "vout_max_after_step_v": round(max(post_step_vout), 4),
            "vout_transient_deviation_mv": round(
                max(abs(max(post_step_vout) - spec.output_voltage_v), abs(spec.output_voltage_v - min(post_step_vout))) * 1000.0,
                3,
            ),
            "inductor_peak_a": round(max(il), 3),
            "inductor_valley_a": round(min(il), 3),
            "load_step_from_a": round(low_load_a, 3),
            "load_step_to_a": round(spec.output_current_a, 3),
            "duty_nominal": round(duty, 4),
            "switching_frequency_hz": fsw,
            "estimated_loss_w": float(loss_result["loss_breakdown"]["total_loss_w"]),
            "sample_count": samples,
            "signoff_status": "not_signoff_synthetic",
        }
        sim = SimulationResult(
            backend="synthetic",
            metrics=metrics,
            waveforms={
                "time_us": time_us,
                "vout_v": vout,
                "il_a": il,
                "switch_v": switch,
                "load_current_a": load_current,
                "duty_command": duty_command,
            },
            notes=[
                "Synthetic backend is used when PLECS/LTspice are not configured.",
                "Waveform shape is intended for workflow validation, not signoff.",
            ],
        )
        sim_dict = sim.to_dict()
        sim_dict["limit_bands"] = limit_bands
        sim_dict["events"] = events
        sim_dict["source_badge"] = "synthetic: workflow demo only, not signoff"
        summary = (
            f"Synthetic open-loop sim produced {samples} samples; "
            f"Vout ripple {metrics['vout_ripple_mv_pp']:.1f}mVpp and IL peak {metrics['inductor_peak_a']:.2f}A."
        )
        return self.complete(
            state,
            SkillRunResult(self.module_id, self.title, summary, {"simulation_result": sim_dict}, source="synthetic"),
        )
