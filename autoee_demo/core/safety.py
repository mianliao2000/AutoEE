from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, Set


RISKY_ACTIONS: Set[str] = {
    "manufacturing_order",
    "export_production_manufacturing_package",
    "firmware_flash",
    "high_voltage_test",
    "high_current_test",
    "change_protection_thresholds",
    "change_gate_timing",
    "bypass_drc_erc_failures",
    "select_final_power_semiconductor",
    "change_isolation_assumptions",
    "change_creepage_clearance",
    "mark_validated",
    "mark_production_ready",
}


@dataclass
class ApprovalCheck:
    action: str
    requires_approval: bool
    allowed: bool
    dry_run: bool
    reason: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def requires_approval(action: str) -> bool:
    return action in RISKY_ACTIONS


def _env_approved() -> bool:
    return os.environ.get("HARDWARE_AGENT_APPROVAL", "").upper() == "YES"


def check_approval(action: str, approve: bool = False, dry_run: bool = True) -> ApprovalCheck:
    """Mechanical approval gate for physical-world or manufacturing actions."""

    risky = requires_approval(action)
    approved = approve or _env_approved()
    if not risky:
        return ApprovalCheck(action, False, True, dry_run, "Action is not registered as risky.")
    if dry_run:
        return ApprovalCheck(action, True, True, True, "Dry-run allowed; real execution remains blocked.")
    if approved:
        return ApprovalCheck(action, True, True, False, "Explicit approval present.")
    return ApprovalCheck(
        action,
        True,
        False,
        False,
        "Blocked: risky hardware action requires --approve or HARDWARE_AGENT_APPROVAL=YES.",
    )
