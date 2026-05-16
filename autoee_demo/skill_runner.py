from __future__ import annotations

import importlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from autoee_demo.core.state import DesignState


@dataclass
class LocalSkillRunResult:
    run_id: str
    skill_id: str
    module_id: str
    status: str
    started_at: str
    completed_at: str
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "runId": self.run_id,
            "skillId": self.skill_id,
            "moduleId": self.module_id,
            "status": self.status,
            "startedAt": self.started_at,
            "completedAt": self.completed_at,
            "artifacts": self.artifacts,
            "logs": self.logs,
            "warnings": self.warnings,
            "errors": self.errors,
            "data": self.data,
        }


SKILL_REGISTRY: Dict[str, Dict[str, str]] = {
    "power.buck_analysis": {
        "module_id": "power_buck_analysis",
        "tab_id": "analysis",
        "module": "skills.power.buck_analysis.run",
        "artifact_dir": "analysis",
    },
    "power.buck_simulation": {
        "module_id": "power_buck_simulation",
        "tab_id": "simulation",
        "module": "skills.power.buck_simulation.run",
        "artifact_dir": "simulation",
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def _skill_input(skill_id: str, raw_input: Optional[Dict[str, Any]], state: DesignState, run_id: str) -> Dict[str, Any]:
    payload = dict(raw_input or {})
    payload.setdefault("skillId", skill_id)
    payload.setdefault("runId", run_id)
    payload.setdefault("spec", state.spec.to_dict())
    payload.setdefault("projectState", state.model_context_payload())
    return payload


def run_local_skill(
    *,
    skill_id: str,
    input_data: Optional[Dict[str, Any]],
    state: DesignState,
    output_root: Path,
) -> LocalSkillRunResult:
    if skill_id not in SKILL_REGISTRY:
        raise ValueError(f"Unknown skill id: {skill_id}")
    meta = SKILL_REGISTRY[skill_id]
    run_id = _run_id()
    started_at = _utc_now()
    run_dir = output_root / run_id / meta["artifact_dir"]
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = _skill_input(skill_id, input_data, state, run_id)
    (run_dir / "skill_input.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    module_id = meta["module_id"]
    try:
        module = importlib.import_module(meta["module"])
        data = module.run(payload, run_dir)
        artifacts = list(data.get("artifacts") or [])
        status = str(data.get("status") or "completed")
        warnings = list(data.get("warnings") or [])
        errors: List[str] = []
    except Exception as exc:
        data = {}
        artifacts = []
        status = "failed"
        warnings = []
        errors = [f"{type(exc).__name__}: {exc}"]
        (run_dir / "skill_error.txt").write_text(errors[0], encoding="utf-8")
    completed_at = _utc_now()
    result = LocalSkillRunResult(
        run_id=run_id,
        skill_id=skill_id,
        module_id=module_id,
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        artifacts=artifacts,
        logs=[str(run_dir / "analysis_log.txt") if meta["artifact_dir"] == "analysis" else str(run_dir / "simulation_log.txt")],
        warnings=warnings,
        errors=errors,
        data=data,
    )
    if status == "completed":
        state.deterministic_results[module_id] = data
        state.ai_notes[module_id] = str(data.get("summary", {}).get("model") or data.get("source") or "Skill completed.")
        state.record_event(meta["tab_id"], "complete", f"{skill_id} completed. Generated {len(artifacts)} artifacts.")
    else:
        state.record_event(meta["tab_id"], "error", f"{skill_id} failed: {'; '.join(errors)}")
    return result

