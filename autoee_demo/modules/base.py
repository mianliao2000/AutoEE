from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from autoee_demo.core.state import ArtifactRef, DesignState
from autoee_demo.model_backend import ModelManager


@dataclass
class SkillRunResult:
    module_id: str
    title: str
    summary: str
    data: Dict[str, Any]
    source: str = "deterministic"
    artifacts: List[ArtifactRef] = field(default_factory=list)


class AutoEESkill(ABC):
    module_id: str = ""
    title: str = ""
    description: str = ""

    @abstractmethod
    def run(
        self,
        state: DesignState,
        model_manager: Optional[ModelManager] = None,
        output_dir: Optional[Path] = None,
    ) -> SkillRunResult:
        raise NotImplementedError

    def ai_explain(
        self,
        state: DesignState,
        model_manager: Optional[ModelManager],
        prompt: str,
    ) -> str:
        if model_manager is None:
            return "AI unavailable: no model manager configured."
        response = model_manager.chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are AutoEE's engineering agent. Explain trade-offs briefly. "
                        "Do not replace deterministic calculations."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            context=state.model_context_payload(),
        )
        return response.text

    def complete(self, state: DesignState, result: SkillRunResult) -> SkillRunResult:
        state.deterministic_results[result.module_id] = result.data
        state.ai_notes[result.module_id] = result.summary
        for artifact in result.artifacts:
            state.artifacts.append(artifact)
        state.record_event(result.module_id, "complete", result.summary)
        return result


def require_result(state: DesignState, module_id: str) -> Dict[str, Any]:
    value = state.deterministic_results.get(module_id)
    if not isinstance(value, dict):
        raise RuntimeError(f"Required module result is missing: {module_id}")
    return value

