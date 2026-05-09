# AutoEE Spec Format

`specs/current_spec.yaml` is the repo-level source of truth for the hardware
design brief. The Python demo keeps using `ProjectSpec`; the adapter in
`autoee_demo.core.spec_adapter` maps between the dataclass and this YAML shape.

Rules:

- Use explicit units in field names, such as `_v`, `_a`, `_w`, `_hz`, `_c`.
- Unknown values must be `null`; do not invent values to satisfy the schema.
- Mock/synthetic assumptions belong in `assumptions`.
- Missing product decisions belong in `open_questions`.
- Physical-world actions must reference `safety/approval_gates.md`.
