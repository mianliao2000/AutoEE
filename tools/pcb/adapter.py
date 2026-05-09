from __future__ import annotations

from typing import Dict

from autoee_demo.core.safety import check_approval


def run_erc(project_path: str) -> Dict[str, object]:
    return {"status": "not_configured", "project_path": project_path}


def run_drc(project_path: str) -> Dict[str, object]:
    return {"status": "not_configured", "project_path": project_path}


def export_manufacturing_files(project_path: str, dry_run: bool = True, approve: bool = False) -> Dict[str, object]:
    approval = check_approval("export_production_manufacturing_package", approve=approve, dry_run=dry_run)
    return {"status": "dry_run" if approval.allowed and dry_run else "blocked", "approval": approval.to_dict(), "project_path": project_path}


def evaluate_layout(project_path: str, constraints: Dict[str, object]) -> Dict[str, object]:
    return {"status": "not_configured", "project_path": project_path, "constraints": constraints}
