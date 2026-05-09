# AutoEE Evaluation Framework

This evaluator is the first hardware-equivalent of a test runner. It reads an
AutoEE `design_state.json`, checks the current design artifacts, and reports
what is complete, partial, missing, or blocked by approval.

Run:

```powershell
python evals/evaluate_design.py --state results/path/design_state.json --out reports
```

Important rules:

- Mock catalogs and synthetic simulations are never marked as signoff-ready.
- Missing hardware artifacts are reported as missing instead of being inferred.
- Manufacturing, firmware flashing, high-voltage tests, and high-current tests
  remain blocked unless an explicit mechanical approval is present.
