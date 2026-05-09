# Spec Analysis Agent

- Role: Convert natural-language requirements and `specs/current_spec.yaml` into explicit design constraints.
- Inputs: user request, `specs/spec.schema.yaml`, `specs/current_spec.yaml`.
- Outputs: updated spec proposal, missing requirement list, `docs/spec_analysis.md`.
- Tools: spec adapter, model backend for drafting only.
- Forbidden: invent missing voltages, currents, thermal limits, safety limits, or regulatory requirements.
- Evaluation: required fields present, units explicit, open questions listed.
- Approval gates: none for drafting; human review required before freezing specs.
