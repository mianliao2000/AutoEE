# AutoEE Evaluation Summary

Overall status: `missing`

This initial repo-level file is a seed. Running the validation skill or:

```powershell
python evals/evaluate_design.py --state results/path/design_state.json --out reports
```

will overwrite it with evaluation output for a concrete `design_state.json`.

Current known missing data includes selected BOM evidence, loss breakdown,
simulation output, control output, schematic/layout files, and manufacturing
artifacts. Manufacturing and firmware actions are blocked by approval gates.
