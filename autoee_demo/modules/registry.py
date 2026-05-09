from __future__ import annotations

from typing import List

from .base import AutoEESkill
from .component_search import ComponentSearchBackend
from .control import ControlTunerBackend
from .emag import EmagSimulationBackend
from .library_pcb import LibraryPcbMechanicalSkill
from .loss_thermal import LossEstimator
from .report_generator import ReportGenerator
from .simulation import CircuitSimulationBackend
from .skill_memory import SkillMemoryWriter
from .spec_analyzer import SpecAnalyzer
from .validation import ValidationSkill


def build_default_skills() -> List[AutoEESkill]:
    return [
        SpecAnalyzer(),
        ComponentSearchBackend(),
        LossEstimator(),
        CircuitSimulationBackend(),
        EmagSimulationBackend(),
        ControlTunerBackend(),
        LibraryPcbMechanicalSkill(),
        ValidationSkill(),
        ReportGenerator(),
        SkillMemoryWriter(),
    ]
