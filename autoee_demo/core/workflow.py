from __future__ import annotations

from typing import Optional

from autoee_demo.model_backend import ModelManager

from .agent import AutoEEAgent
from .state import DesignState, utc_now_iso


def run_synthetic_workflow(
    state: Optional[DesignState] = None,
    model_manager: Optional[ModelManager] = None,
) -> DesignState:
    """Run a deterministic smoke workflow that does not need external tools."""

    design_state = state or DesignState()
    spec = design_state.spec
    output_power_w = spec.output_voltage_v * spec.output_current_a
    estimated_loss_w = output_power_w * (100.0 / spec.target_efficiency_percent - 1.0)
    design_state.workflow_status = "synthetic_complete"
    design_state.deterministic_results["synthetic_workflow"] = {
        "output_power_w": round(output_power_w, 3),
        "estimated_loss_w": round(estimated_loss_w, 3),
        "backend": "synthetic",
        "note": "Smoke workflow only; engineering modules replace this with real calculations.",
    }

    if model_manager is not None:
        response = model_manager.chat(
            messages=[
                {
                    "role": "system",
                    "content": "You are an AutoEE engineering assistant. Keep the response short.",
                },
                {
                    "role": "user",
                    "content": (
                        "Summarize the synthetic Buck charger workflow status and mention that "
                        "deterministic modules own numeric calculations."
                    ),
                },
            ],
            context=design_state.model_context_payload(),
        )
        design_state.ai_notes["synthetic_workflow"] = response.text

    design_state.updated_at = utc_now_iso()
    return design_state


def run_full_demo_workflow(
    state: Optional[DesignState] = None,
    model_manager: Optional[ModelManager] = None,
) -> DesignState:
    """Run every AutoEE demo skill with mock/synthetic fallbacks."""

    agent = AutoEEAgent(state=state or DesignState(), model_manager=model_manager)
    agent.run_all()
    agent.state.updated_at = utc_now_iso()
    return agent.state
