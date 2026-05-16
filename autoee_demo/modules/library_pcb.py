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
        automation_steps = [
            {
                "step": "Datasheet Extraction",
                "status": "demo_data",
                "output": "outputs/datasheet_fields.json",
                "artifactPath": "fake://datasheets/extracted_package_pin_land_pattern.json",
                "notice": "Not connected to real datasheet parsing yet.",
            },
            {
                "step": "Symbol Generation",
                "status": "demo_data",
                "output": "libs/kicad/AutoEE_Demo.kicad_sym",
                "artifactPath": "fake://kicad/symbols/AutoEE_Demo.kicad_sym",
                "notice": "Not connected to real KiCad symbol writer yet.",
            },
            {
                "step": "Footprint Generation",
                "status": "demo_data",
                "output": "libs/kicad/AutoEE_Demo.pretty/*.kicad_mod",
                "artifactPath": "fake://kicad/footprints/AutoEE_Demo.pretty",
                "notice": "Not connected to real footprint generation yet.",
            },
            {
                "step": "Schematic Generation",
                "status": "demo_data",
                "output": "AutoEE_usb_c_buck.kicad_sch",
                "artifactPath": "fake://kicad/project/AutoEE_usb_c_buck.kicad_sch",
                "notice": "Not connected to real KiCad schematic automation yet.",
            },
            {
                "step": "Placement",
                "status": "demo_data",
                "output": "placement_plan.json",
                "artifactPath": "fake://layout/placement/hot_loop_minimized.json",
                "notice": "Not connected to real placement optimizer yet.",
            },
            {
                "step": "Routing",
                "status": "demo_data",
                "output": "routing_plan.json",
                "artifactPath": "fake://layout/routing/power_and_signal_routes.json",
                "notice": "Not connected to real autorouter yet.",
            },
            {
                "step": "DRC / ERC",
                "status": "demo_data",
                "output": "reports/drc_erc_summary.md",
                "artifactPath": "fake://reports/drc_erc_summary.md",
                "notice": "Not connected to real KiCad DRC/ERC yet.",
            },
            {
                "step": "Gerber Export",
                "status": "demo_data",
                "output": "manufacturing/gerbers/AutoEE_usb_c_buck.zip",
                "artifactPath": "fake://manufacturing/gerbers/AutoEE_usb_c_buck.zip",
                "notice": "No real Gerber files are created in this demo.",
            },
            {
                "step": "JLCPCB Handoff",
                "status": "blocked_not_connected",
                "output": "manufacturing/jlcpcb_order_payload.json",
                "artifactPath": "fake://manufacturing/jlcpcb_order_payload.json",
                "notice": "Not connected to real JLCPCB API; no order is placed.",
            },
        ]
        summary = "Prepared KiCad/FreeCAD artifact plan and reserved PCB/manufacturing/firmware interfaces."
        return self.complete(
            state,
            SkillRunResult(
                self.module_id,
                self.title,
                summary,
                {
                    "library_generation_plan": plan,
                    "downstream_interfaces": downstream,
                    "automation_steps": automation_steps,
                    "sourceType": "fake_kicad_jlcpcb_pipeline",
                    "realCapabilityStatus": "not_connected",
                    "capabilityNotice": "Demo data only. KiCad, FreeCAD, Gerber export, and JLCPCB ordering are not connected.",
                },
                source="placeholder",
            ),
        )
