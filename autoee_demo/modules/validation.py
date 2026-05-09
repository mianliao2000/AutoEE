from __future__ import annotations

from pathlib import Path
from typing import Optional

from autoee_demo.core.state import ArtifactRef, DesignState
from autoee_demo.model_backend import ModelManager
from evals.metrics import evaluate_design_state, write_evaluation_reports

from .base import AutoEESkill, SkillRunResult


class ValidationSkill(AutoEESkill):
    module_id = "validation"
    title = "Evaluation"
    description = "Evaluate design completeness, risks, missing data, and approval-blocked actions."

    def run(
        self,
        state: DesignState,
        model_manager: Optional[ModelManager] = None,
        output_dir: Optional[Path] = None,
    ) -> SkillRunResult:
        root = output_dir or Path("reports")
        summary = evaluate_design_state(state)
        paths = write_evaluation_reports(summary, root)
        artifacts = [
            ArtifactRef(kind="eval_summary_json", path=paths["eval_summary_json"], source="evaluation"),
            ArtifactRef(kind="eval_summary_markdown", path=paths["eval_summary_markdown"], source="evaluation"),
        ]
        message = (
            f"Evaluation overall status is {summary.overall_status}; "
            f"{len(summary.missing_data)} missing data items and {len(summary.risks)} risks recorded."
        )
        return self.complete(
            state,
            SkillRunResult(
                self.module_id,
                self.title,
                message,
                {"evaluation_summary": summary.to_dict(), **paths},
                source="deterministic_evaluator",
                artifacts=artifacts,
            ),
        )
