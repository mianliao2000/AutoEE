from __future__ import annotations

from typing import Dict

from autoee_demo.core.safety import check_approval


def generate_pwm_config(spec: Dict[str, object]) -> Dict[str, object]:
    return {"status": "planned", "spec_keys": sorted(spec.keys())}


def generate_adc_config(spec: Dict[str, object]) -> Dict[str, object]:
    return {"status": "planned", "spec_keys": sorted(spec.keys())}


def build_firmware(project_path: str) -> Dict[str, object]:
    return {"status": "not_configured", "project_path": project_path}


def flash_firmware(project_path: str, approve: bool = False, dry_run: bool = True) -> Dict[str, object]:
    approval = check_approval("firmware_flash", approve=approve, dry_run=dry_run)
    return {"status": "dry_run" if approval.allowed and dry_run else "blocked", "approval": approval.to_dict(), "project_path": project_path}
