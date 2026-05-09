from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from autoee_demo.core.state import ArtifactRef, DesignState
from autoee_demo.model_backend import ModelManager

from .base import AutoEESkill, SkillRunResult


def _loss_bars(items):
    if not items:
        return []
    max_value = max(items.values()) or 1.0
    lines = []
    for key, value in sorted(items.items(), key=lambda item: item[1], reverse=True):
        bar = "#" * max(1, int(value / max_value * 28))
        lines.append(f"- {key}: {value:.4f} W `{bar}`")
    return lines


class ReportGenerator(AutoEESkill):
    module_id = "report_generator"
    title = "Report"
    description = "Export design_state.json and a human-readable Markdown signoff report."

    def run(
        self,
        state: DesignState,
        model_manager: Optional[ModelManager] = None,
        output_dir: Optional[Path] = None,
    ) -> SkillRunResult:
        root = output_dir or Path("results") / f"autoee_demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        root.mkdir(parents=True, exist_ok=True)
        state_path = root / "design_state.json"
        report_path = root / "report.md"
        state.save_json(state_path)
        loss = state.deterministic_results.get("loss_thermal", {}).get("loss_breakdown", {})
        thermal = state.deterministic_results.get("loss_thermal", {}).get("thermal_result", {})
        sim = state.deterministic_results.get("open_loop_sim", {}).get("simulation_result", {})
        control = state.deterministic_results.get("closed_loop_control", {}).get("control_result", {})
        evaluation = state.deterministic_results.get("validation", {}).get("evaluation_summary", {})
        lines = [
            "# AutoEE Buck Workflow Demo Report",
            "",
            "## Goal",
            "15W vehicle/industrial USB-C synchronous Buck charger workflow demo.",
            "",
            "## Spec",
            "```json",
            json.dumps(state.spec.to_dict(), indent=2, sort_keys=True),
            "```",
            "",
            "## Loss Breakdown",
            *(_loss_bars(loss.get("items_w", {})) or ["- Not available"]),
            "",
            f"Total loss: {loss.get('total_loss_w', 'n/a')} W",
            f"Efficiency: {loss.get('efficiency_percent', 'n/a')} %",
            "",
            "## Thermal",
            "```json",
            json.dumps(thermal, indent=2, sort_keys=True),
            "```",
            "",
            "## Simulation",
            "```json",
            json.dumps(sim.get("metrics", {}), indent=2, sort_keys=True),
            "```",
            "",
            "## Control",
            "```json",
            json.dumps(control, indent=2, sort_keys=True),
            "```",
            "",
            "## Evaluation",
            "```json",
            json.dumps(evaluation, indent=2, sort_keys=True),
            "```",
            "",
            "## Human Signoff Checklist",
            "- Confirm all mock catalog parts against real datasheets.",
            "- Replace synthetic simulation with PLECS/LTspice before design signoff.",
            "- Replace Maxwell placeholder with real magnetic/EMI analysis.",
            "- Review KiCad land patterns and 3D STEP models before PCB release.",
            "- Validate thermal model with board-level measurement or detailed simulation.",
            "- Keep manufacturing, firmware flashing, and lab testing blocked until explicit mechanical approval is present.",
        ]
        report_path.write_text("\n".join(lines), encoding="utf-8")
        artifacts = [
            ArtifactRef(kind="design_state", path=str(state_path), source="generated_report"),
            ArtifactRef(kind="markdown_report", path=str(report_path), source="generated_report"),
        ]
        summary = f"Exported report package to {root}."
        return self.complete(
            state,
            SkillRunResult(
                self.module_id,
                self.title,
                summary,
                {"report_dir": str(root), "design_state": str(state_path), "markdown_report": str(report_path)},
                artifacts=artifacts,
            ),
        )
