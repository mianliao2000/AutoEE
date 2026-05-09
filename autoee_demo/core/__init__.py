"""Shared deterministic state and workflow helpers."""

from .agent import AutoEEAgent
from .safety import ApprovalCheck, check_approval, requires_approval
from .spec_adapter import load_project_spec_yaml, save_project_spec_yaml
from .state import (
    ArtifactRef,
    BomSelection,
    ControlResult,
    DesignCandidate,
    DesignState,
    LossBreakdown,
    PartCandidate,
    ProgressEvent,
    ProjectSpec,
    SimulationResult,
    ThermalResult,
)
from .workflow import run_synthetic_workflow

__all__ = [
    "ArtifactRef",
    "ApprovalCheck",
    "AutoEEAgent",
    "BomSelection",
    "ControlResult",
    "DesignCandidate",
    "DesignState",
    "LossBreakdown",
    "PartCandidate",
    "ProgressEvent",
    "ProjectSpec",
    "SimulationResult",
    "ThermalResult",
    "run_synthetic_workflow",
    "check_approval",
    "load_project_spec_yaml",
    "requires_approval",
    "save_project_spec_yaml",
]
