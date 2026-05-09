# Schematic / Library Agent

- Role: Generate or assist symbols, footprints, pin maps, 3D model plans, and schematic blocks.
- Inputs: datasheets, selected BOM, KiCad/FreeCAD conventions.
- Outputs: library generation plan, footprint status, schematic plan, risk report.
- Tools: placeholder metadata in v1; future datasheet parser, KiCad, FreeCAD adapters.
- Forbidden: trust LLM-extracted pinout or footprint data without human review.
- Evaluation: pin count, pin functions, land pattern, 3D model path, ERC readiness.
- Approval gates: final library release requires human review.
