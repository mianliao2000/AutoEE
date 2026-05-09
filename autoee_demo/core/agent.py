from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional

from autoee_demo.core.state import DesignState
from autoee_demo.model_backend import ModelManager
from autoee_demo.modules import build_default_skills
from autoee_demo.modules.base import AutoEESkill, SkillRunResult


class AutoEEAgent:
    """Small agent orchestrator that treats each module as a skill."""

    def __init__(
        self,
        state: Optional[DesignState] = None,
        model_manager: Optional[ModelManager] = None,
        skills: Optional[Iterable[AutoEESkill]] = None,
    ):
        self.state = state or DesignState()
        self.model_manager = model_manager
        self.skills: List[AutoEESkill] = list(skills or build_default_skills())
        self.skill_map: Dict[str, AutoEESkill] = {skill.module_id: skill for skill in self.skills}
        self.stop_requested = False

    def run_skill(self, module_id: str, output_dir: Optional[Path] = None) -> SkillRunResult:
        if module_id not in self.skill_map:
            raise ValueError(f"Unknown AutoEE skill: {module_id}")
        self.state.record_event(module_id, "running", "Module started.")
        result = self.skill_map[module_id].run(self.state, self.model_manager, output_dir=output_dir)
        self.state.workflow_status = "partial" if module_id != "skill_memory" else "complete"
        return result

    def run_all(self, output_dir: Optional[Path] = None) -> List[SkillRunResult]:
        self.stop_requested = False
        results: List[SkillRunResult] = []
        for skill in self.skills:
            if self.stop_requested:
                self.state.record_event(skill.module_id, "stopped", "Run stopped before this module.")
                break
            results.append(self.run_skill(skill.module_id, output_dir=output_dir))
        if not self.stop_requested:
            self.state.workflow_status = "complete"
        return results

    def stop(self) -> None:
        self.stop_requested = True
        self.state.workflow_status = "stop_requested"
        self.state.record_event("agent", "stop_requested", "Stop requested by user.")

    def reset_module(self, module_id: str) -> None:
        self.state.clear_from([module_id])
        self.state.record_event(module_id, "reset", "Module result cleared.")

    def reset_all(self) -> None:
        self.state = DesignState(spec=self.state.spec)
        self.stop_requested = False

