from __future__ import annotations

from typing import Dict

from autoee_demo.core.safety import check_approval


def collect_scope_data(config: Dict[str, object]) -> Dict[str, object]:
    return {"status": "not_configured", "dry_run": True, "config": config}


def collect_power_analyzer_data(config: Dict[str, object]) -> Dict[str, object]:
    return {"status": "not_configured", "dry_run": True, "config": config}


def run_test_matrix(config: Dict[str, object], approve: bool = False, dry_run: bool = True) -> Dict[str, object]:
    approval = check_approval("high_current_test", approve=approve, dry_run=dry_run)
    return {"status": "dry_run" if approval.allowed and dry_run else "blocked", "approval": approval.to_dict(), "config": config}


def analyze_waveform(waveform_path: str) -> Dict[str, object]:
    return {"status": "not_configured", "waveform_path": waveform_path}
