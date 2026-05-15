from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, Optional

from autoee_demo.core.state import DesignState, LossBreakdown, ThermalResult
from autoee_demo.model_backend import ModelManager

from .base import AutoEESkill, SkillRunResult, require_result


def _ripple_current(vin: float, vout: float, inductance_h: float, fsw_hz: float) -> float:
    duty = vout / vin
    return (vout * (1.0 - duty)) / (inductance_h * fsw_hz)


def _rds_temp(rds_25_ohm: float, temp_c: float) -> float:
    return rds_25_ohm * (1.0 + 0.004 * (temp_c - 25.0))


def _dcr_temp(dcr_25_ohm: float, temp_c: float) -> float:
    return dcr_25_ohm * (1.0 + 0.0039 * (temp_c - 25.0))


class LossEstimator(AutoEESkill):
    module_id = "loss_thermal"
    title = "Loss + Thermal"
    description = "One-stage power loss and thermal estimate for the Buck charger."

    def run(
        self,
        state: DesignState,
        model_manager: Optional[ModelManager] = None,
        output_dir: Optional[Path] = None,
    ) -> SkillRunResult:
        spec_result = require_result(state, "spec_analyzer")
        bom_result = require_result(state, "component_search")
        spec = state.spec
        candidate = spec_result["selected_candidate"]
        bom = bom_result["selected_bom"]

        vin = spec.input_voltage_nominal_v
        vout = spec.output_voltage_v
        iout = spec.output_current_a
        fsw = float(candidate["switching_frequency_hz"])
        inductance_h = float(candidate["inductor_uh"]) * 1e-6
        duty = vout / vin
        ripple_a = _ripple_current(spec.input_voltage_max_v, vout, inductance_h, fsw)
        il_rms = math.sqrt(iout * iout + ripple_a * ripple_a / 12.0)
        icout_rms = ripple_a / (2.0 * math.sqrt(3.0))
        icin_rms = iout * math.sqrt(duty * (1.0 - duty))

        hs_params = bom["high_side_mosfet"]["key_params"]
        ls_params = bom["low_side_mosfet"]["key_params"]
        ind_params = bom["inductor"]["key_params"]
        cin_params = bom["input_capacitor"]["key_params"]
        cout_params = bom["output_capacitor"]["key_params"]

        hs_temp = spec.ambient_temp_c + 20.0
        ls_temp = spec.ambient_temp_c + 18.0
        ind_temp = spec.ambient_temp_c + 15.0
        items: Dict[str, float] = {}
        component_loss = {}
        for _ in range(3):
            hs_rds = _rds_temp(float(hs_params["rds_on_mohm_25c"]) * 1e-3, hs_temp)
            ls_rds = _rds_temp(float(ls_params["rds_on_mohm_25c"]) * 1e-3, ls_temp)
            dcr = _dcr_temp(float(ind_params["dcr_mohm_25c"]) * 1e-3, ind_temp)
            items = {
                "hs_mosfet_conduction": il_rms * il_rms * hs_rds * duty,
                "ls_mosfet_conduction": il_rms * il_rms * ls_rds * (1.0 - duty),
                "hs_switching_overlap": 0.5 * vin * iout * (float(hs_params["tr_ns"]) + float(hs_params["tf_ns"])) * 1e-9 * fsw,
                "gate_drive": (float(hs_params["qg_nc"]) + float(ls_params["qg_nc"])) * 1e-9 * 7.5 * fsw,
                "coss_eoss": 0.5 * (float(hs_params["coss_pf"]) + float(ls_params["coss_pf"])) * 1e-12 * vin * vin * fsw,
                "body_diode_deadtime": iout * 0.75 * (30e-9 * 2.0 * fsw),
                "reverse_recovery_placeholder": 0.035,
                "inductor_dcr": il_rms * il_rms * dcr,
                "inductor_core_placeholder": float(ind_params.get("core_loss_w_est", 0.18)),
                "output_cap_esr": icout_rms * icout_rms * (float(cout_params["esr_mohm"]) * 1e-3 / float(cout_params["parallel_count"])),
                "input_cap_rms_esr": icin_rms * icin_rms * (float(cin_params["esr_mohm"]) * 1e-3 / float(cin_params["parallel_count"])),
                "pcb_pdn_cable_contact": iout * iout * 0.020,
            }
            component_loss = {
                "high_side_mosfet": items["hs_mosfet_conduction"] + items["hs_switching_overlap"] + items["gate_drive"] / 2 + items["coss_eoss"] / 2,
                "low_side_mosfet": items["ls_mosfet_conduction"] + items["body_diode_deadtime"] + items["gate_drive"] / 2 + items["coss_eoss"] / 2,
                "inductor": items["inductor_dcr"] + items["inductor_core_placeholder"],
                "capacitors_and_pdn": items["output_cap_esr"] + items["input_cap_rms_esr"] + items["pcb_pdn_cable_contact"],
            }
            hs_temp = spec.ambient_temp_c + component_loss["high_side_mosfet"] * 45.0
            ls_temp = spec.ambient_temp_c + component_loss["low_side_mosfet"] * 45.0
            ind_temp = spec.ambient_temp_c + component_loss["inductor"] * 35.0

        total_loss = sum(items.values())
        output_power = vout * iout
        input_power = output_power + total_loss
        efficiency = output_power / input_power * 100.0
        loss = LossBreakdown(
            items_w={key: round(value, 4) for key, value in items.items()},
            total_loss_w=round(total_loss, 4),
            output_power_w=round(output_power, 4),
            input_power_w=round(input_power, 4),
            efficiency_percent=round(efficiency, 3),
            confidence="medium",
            notes=[
                "MOSFET switching model is first-order; CSI and layout parasitics are placeholders.",
                "Core loss uses mock datasheet estimate and requires human signoff.",
                "RthetaJA is board and airflow dependent, not a package-only constant.",
            ],
        )
        temps = {
            "high_side_mosfet_junction": round(hs_temp, 2),
            "low_side_mosfet_junction": round(ls_temp, 2),
            "inductor_hotspot": round(ind_temp, 2),
            "automotive_85c_high_side_estimate": round(spec.automotive_warning_ambient_c + component_loss["high_side_mosfet"] * 45.0, 2),
        }
        warnings = []
        if total_loss > spec.max_total_loss_w:
            warnings.append("Total loss exceeds target; trade off MOSFET, fsw, inductor DCR, or thermal path.")
        if efficiency < spec.target_efficiency_percent:
            warnings.append("Efficiency is below target.")
        if max(temps.values()) > 125.0:
            warnings.append("Thermal estimate exceeds 125C warning threshold.")
        thermal = ThermalResult(
            component_temps_c=temps,
            max_junction_temp_c=max(temps.values()),
            warnings=warnings,
            model_notes=[
                "Tj = Ta + P * RthetaJA_eff is used for v1.",
                "Future path preserves RthetaJC + interface + heatsink/PCB modeling.",
            ],
        )
        summary = (
            f"Estimated {loss.total_loss_w:.2f}W loss and {loss.efficiency_percent:.1f}% efficiency; "
            f"max temperature estimate {thermal.max_junction_temp_c:.1f}C."
        )
        summary_cards = [
            {
                "label": "Total Loss",
                "value": loss.total_loss_w,
                "display": f"{loss.total_loss_w:.2f} W",
                "status": "pass" if loss.total_loss_w <= spec.max_total_loss_w else "warn",
                "note": "First-order estimate from fake datasheet-like parameters.",
            },
            {
                "label": "Efficiency",
                "value": loss.efficiency_percent,
                "display": f"{loss.efficiency_percent:.2f}%",
                "status": "pass" if loss.efficiency_percent >= spec.target_efficiency_percent else "warn",
                "note": "Not signoff; replace with bench and simulation correlation.",
            },
            {
                "label": "Max Temperature",
                "value": thermal.max_junction_temp_c,
                "display": f"{thermal.max_junction_temp_c:.1f} C",
                "status": "warn" if thermal.max_junction_temp_c >= spec.automotive_warning_ambient_c else "pass",
                "note": "Board airflow, copper area, and package thermal path are placeholders.",
            },
            {
                "label": "Model Status",
                "value": "demo_estimate_not_signoff",
                "display": "Demo estimate",
                "status": "demo",
                "note": "Real thermal simulation and lab measurement are not connected yet.",
            },
        ]
        return self.complete(
            state,
            SkillRunResult(
                module_id=self.module_id,
                title=self.title,
                summary=summary,
                data={
                    "loss_breakdown": loss.to_dict(),
                    "thermal_result": thermal.to_dict(),
                    "derived": {
                        "duty_nominal": round(duty, 4),
                        "inductor_ripple_a_at_vin_max": round(ripple_a, 4),
                        "inductor_rms_a": round(il_rms, 4),
                        "input_cap_rms_a": round(icin_rms, 4),
                        "output_cap_rms_a": round(icout_rms, 4),
                    },
                    "summary_cards": summary_cards,
                    "sourceType": "first_order_demo_model",
                    "realCapabilityStatus": "demo_estimate_not_signoff",
                },
            ),
        )
