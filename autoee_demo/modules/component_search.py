from __future__ import annotations

from pathlib import Path
from typing import Optional

from autoee_demo.core.state import BomSelection, DesignState, PartCandidate
from autoee_demo.model_backend import ModelManager

from .base import AutoEESkill, SkillRunResult, require_result


def _part(category, mpn, manufacturer, params, price, stock, footprint):
    return PartCandidate(
        category=category,
        mpn=mpn,
        manufacturer=manufacturer,
        key_params=params,
        unit_price_usd=price,
        stock_qty=stock,
        footprint=footprint,
        source="mock_digikey_catalog",
    )


class ComponentSearchBackend(AutoEESkill):
    module_id = "component_search"
    title = "BOM Search"
    description = "Mock DigiKey search and ranking for MOSFET, inductor, and capacitor candidates."

    def run(
        self,
        state: DesignState,
        model_manager: Optional[ModelManager] = None,
        output_dir: Optional[Path] = None,
    ) -> SkillRunResult:
        require_result(state, "spec_analyzer")
        spec = state.spec
        required_vds = max(40.0, spec.input_voltage_max_v * 1.25)
        required_current = spec.output_current_a * 2.0
        candidates = {
            "mosfets": [
                _part(
                    "mosfet",
                    "DEMO-FET-60V-6MOHM-QFN5X6",
                    "AutoEE Mock",
                    {"vds_v": 60, "rds_on_mohm_25c": 6.0, "qg_nc": 18, "coss_pf": 450, "tr_ns": 12, "tf_ns": 10},
                    0.58,
                    45000,
                    "PowerPAK_SO8_5x6",
                ),
                _part(
                    "mosfet",
                    "DEMO-FET-40V-3MOHM-QFN5X6",
                    "AutoEE Mock",
                    {"vds_v": 40, "rds_on_mohm_25c": 3.2, "qg_nc": 32, "coss_pf": 720, "tr_ns": 18, "tf_ns": 16},
                    0.74,
                    26000,
                    "PowerPAK_SO8_5x6",
                ),
            ],
            "inductors": [
                _part(
                    "inductor",
                    "DEMO-SHIELDED-10UH-7A",
                    "AutoEE Mock",
                    {"inductance_uh": 10, "dcr_mohm_25c": 22, "isat_a": 8.5, "irms_a": 7.0, "core_loss_w_est": 0.18},
                    0.82,
                    18000,
                    "Inductor_7x7mm",
                ),
                _part(
                    "inductor",
                    "DEMO-SHIELDED-6R8UH-8A",
                    "AutoEE Mock",
                    {"inductance_uh": 6.8, "dcr_mohm_25c": 16, "isat_a": 9.5, "irms_a": 8.0, "core_loss_w_est": 0.24},
                    0.91,
                    12000,
                    "Inductor_7x7mm",
                ),
            ],
            "capacitors": [
                _part(
                    "output_capacitor",
                    "DEMO-X7R-47UF-10V-1210",
                    "AutoEE Mock",
                    {"capacitance_uf_effective": 47, "voltage_rating_v": 10, "esr_mohm": 4.0, "parallel_count": 2},
                    0.19,
                    90000,
                    "C_1210_3225Metric",
                ),
                _part(
                    "input_capacitor",
                    "DEMO-X7R-22UF-50V-1210",
                    "AutoEE Mock",
                    {"capacitance_uf_effective": 22, "voltage_rating_v": 50, "esr_mohm": 3.0, "parallel_count": 2},
                    0.31,
                    65000,
                    "C_1210_3225Metric",
                ),
            ],
        }
        selected = BomSelection(
            high_side_mosfet=candidates["mosfets"][0],
            low_side_mosfet=candidates["mosfets"][1],
            inductor=candidates["inductors"][0],
            input_capacitor=candidates["capacitors"][1],
            output_capacitor=candidates["capacitors"][0],
        )
        summary = (
            f"Selected mock BOM with >= {required_vds:.0f}V MOSFET margin and "
            f">= {required_current:.1f}A inductor current margin."
        )
        return self.complete(
            state,
            SkillRunResult(
                module_id=self.module_id,
                title=self.title,
                summary=summary,
                data={
                    "backend": "mock_digikey",
                    "selected_bom": selected.to_dict(),
                    "candidate_counts": {key: len(value) for key, value in candidates.items()},
                    "selection_rules": [
                        "Voltage rating >= 1.25 x Vin(max)",
                        "Inductor saturation current > Iout + ripple/2",
                        "X7R ceramic caps with voltage derating and low ESR",
                    ],
                },
                source="mock_catalog",
            ),
        )

