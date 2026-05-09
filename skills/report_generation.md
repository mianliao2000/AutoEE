# Skill: Report Generation

Use after a workflow or evaluation run.

Inputs:
- `design_state.json`
- `reports/eval_summary.json`
- Generated artifacts and human notes

Steps:
- Separate measured, simulated, estimated, mock, synthetic, missing, and human-decision-required data.
- Summarize risks and next actions.
- Preserve assumptions and open questions.

Checks:
- Do not hide missing data.
