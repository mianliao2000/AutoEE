from __future__ import annotations

from pathlib import Path
from typing import Optional

from autoee_demo.core.state import DesignState
from autoee_demo.model_backend import ModelManager

from .base import AutoEESkill, SkillRunResult, require_result


class LibraryPcbMechanicalSkill(AutoEESkill):
    module_id = "library_pcb_mechanical"
    title = "KiCad / PCB / 3D"
    description = "Datasheet-to-library, PCB, and FreeCAD/STEP placeholder planning."

    def run(
        self,
        state: DesignState,
        model_manager: Optional[ModelManager] = None,
        output_dir: Optional[Path] = None,
    ) -> SkillRunResult:
        bom = require_result(state, "component_search")["selected_bom"]
        plan = {
            "kicad": {
                "symbol_library": "libs/kicad/AutoEE_Demo.kicad_sym",
                "footprint_library": "libs/kicad/AutoEE_Demo.pretty",
                "footprint_format": ".kicad_mod S-expression",
                "model_path_policy": "${KIPRJMOD}/libs/3d/<part>.step",
            },
            "freecad": {
                "script_stub": "tools/freecad/generate_package_step.py",
                "output_dir": "libs/3d",
                "format": "STEP",
            },
            "datasheet_extraction": {
                "package_model": "reserved",
                "pin_map": "reserved",
                "land_pattern": "reserved",
                "mechanical_envelope": "reserved",
            },
            "selected_parts": [
                bom["high_side_mosfet"]["mpn"],
                bom["low_side_mosfet"]["mpn"],
                bom["inductor"]["mpn"],
                bom["input_capacitor"]["mpn"],
                bom["output_capacitor"]["mpn"],
            ],
        }
        downstream = {
            "schematic_generator": "reserved",
            "layout_backend": "reserved",
            "manufacturing_backend_jlcpcb": "reserved",
            "firmware_backend": "reserved",
            "debug_assistant": "reserved",
            "test_loop_backend": "reserved",
        }
        summary = "Prepared KiCad/FreeCAD artifact plan and reserved PCB/manufacturing/firmware interfaces."
        return self.complete(
            state,
            SkillRunResult(
                self.module_id,
                self.title,
                summary,
                {"library_generation_plan": plan, "downstream_interfaces": downstream},
                source="placeholder",
            ),
        )

