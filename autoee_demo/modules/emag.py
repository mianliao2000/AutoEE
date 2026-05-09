from __future__ import annotations

from pathlib import Path
from typing import Optional

from autoee_demo.core.state import DesignState
from autoee_demo.model_backend import ModelManager

from .base import AutoEESkill, SkillRunResult, require_result


class EmagSimulationBackend(AutoEESkill):
    module_id = "emag_maxwell"
    title = "EM / Maxwell"
    description = "Maxwell job-spec placeholder and magnetic/EMI signoff checklist."

    def run(
        self,
        state: DesignState,
        model_manager: Optional[ModelManager] = None,
        output_dir: Optional[Path] = None,
    ) -> SkillRunResult:
        loss = require_result(state, "loss_thermal")
        derived = loss["derived"]
        checklist = [
            "Minimize hot-loop area: input capacitor, high-side FET, low-side FET return path.",
            "Place high-frequency ceramic input capacitors directly at the half bridge.",
            "Keep SW node copper compact while respecting thermal spreading.",
            "Verify inductor saturation margin at Iout + ripple/2.",
            "Use shielded inductor and inspect near-field emissions around SW and inductor.",
        ]
        job_spec = {
            "tool": "Ansys Maxwell",
            "status": "placeholder",
            "inputs": {
                "inductor_current_peak_a": derived["inductor_ripple_a_at_vin_max"] / 2.0 + state.spec.output_current_a,
                "switching_frequency_hz": require_result(state, "spec_analyzer")["selected_candidate"]["switching_frequency_hz"],
                "core_loss_prior": loss["loss_breakdown"]["items_w"]["inductor_core_placeholder"],
            },
            "expected_outputs": ["core_loss_w", "winding_loss_w", "flux_density_t", "emi_risk_score"],
        }
        summary = "Generated Maxwell placeholder job spec and EMI/hot-loop checklist."
        return self.complete(
            state,
            SkillRunResult(self.module_id, self.title, summary, {"maxwell_job_spec": job_spec, "checklist": checklist}, source="placeholder"),
        )

