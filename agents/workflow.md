# AutoEE Agent Workflow

Loop:

1. Read `specs/current_spec.yaml` and current generated artifacts.
2. Build or update a minimal skill plan.
3. Run deterministic skills and external tool adapters where configured.
4. Run `evals/evaluate_design.py` and review missing data, risks, and blocked actions.
5. Generate reports and update reusable skills.

Rules:

- Operate on files, not only chat memory.
- Preserve existing artifacts unless the change is explicit and reviewable.
- Mark mock, synthetic, placeholder, missing, and requires-human-input data clearly.
- Risky physical or manufacturing actions require the safety approval gate.
