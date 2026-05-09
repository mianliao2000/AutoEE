# AutoEE Next Steps

## Immediate
- Use `specs/current_spec.yaml` as the default project-level design brief.
- Run full workflow, then run validation to produce `reports/eval_summary.json` and `reports/eval_summary.md`.
- Keep all risky operations in dry-run mode.

## Near-Term Engineering
- Implement LLM planner output as an inspectable skill DAG.
- Add distributor-backed component adapter with local cache and CSV fallback.
- Add real PLECS/LTspice adapter for open-loop and closed-loop simulation.
- Add KiCad/FreeCAD artifact generation stubs with pin/footprint review status.

## Later
- Add Maxwell/PyAEDT EM workflows.
- Add firmware generation/build adapters and approval-gated flashing.
- Add lab debug/test-matrix adapters with safety gates.
