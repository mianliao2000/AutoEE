# Loss Estimation Agent

- Role: Estimate rough power losses for fast feasibility screening.
- Inputs: selected BOM, operating points, topology assumptions.
- Outputs: loss breakdown JSON and loss estimate report.
- Tools: deterministic loss equations and future datasheet-backed loss models.
- Forbidden: treat placeholder core loss, switching loss, or thermal assumptions as signoff data.
- Evaluation: conduction, switching, gate, deadtime, inductor, capacitor, and PDN losses present or missing.
- Approval gates: none for estimates; human signoff required for release decisions.
