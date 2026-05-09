from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from autoee_demo.core.state import ArtifactRef, DesignState
from autoee_demo.model_backend import ModelManager

from .base import AutoEESkill, SkillRunResult


class SkillMemoryWriter(AutoEESkill):
    module_id = "skill_memory"
    title = "Skill Memory"
    description = "Persist workflow lessons as reusable skill-memory seeds."

    def run(
        self,
        state: DesignState,
        model_manager: Optional[ModelManager] = None,
        output_dir: Optional[Path] = None,
    ) -> SkillRunResult:
        root = output_dir or Path("results") / "skill_memory"
        root.mkdir(parents=True, exist_ok=True)
        path = root / "buck_charger_demo_memory.json"
        lessons = {
            "scenario": "Vehicle/industrial 9-36V to 5V/3A USB-C Buck charger",
            "module_status": dict(state.module_status),
            "known_placeholders": [
                "mock DigiKey catalog",
                "synthetic simulation",
                "Maxwell placeholder",
                "KiCad/FreeCAD generation plan only",
            ],
            "next_training_targets": [
                "datasheet extraction accuracy",
                "real PLECS/LTspice waveform calibration",
                "thermal model calibration from lab data",
            ],
        }
        path.write_text(json.dumps(lessons, indent=2, sort_keys=True), encoding="utf-8")
        artifact = ArtifactRef(kind="skill_memory", path=str(path), source="generated_memory")
        summary = "Saved reusable Buck charger workflow memory seed."
        return self.complete(
            state,
            SkillRunResult(self.module_id, self.title, summary, {"skill_memory": lessons, "path": str(path)}, artifacts=[artifact]),
        )

