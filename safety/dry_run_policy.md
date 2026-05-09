# AutoEE Dry-Run Policy

Risky hardware operations default to dry-run.

Allowed dry-run examples:

```powershell
python tools/pcb/export_manufacturing.py --dry-run
python tools/firmware/flash.py --dry-run
python lab/run_test_matrix.py --dry-run
```

Real execution must require `--approve` or:

```powershell
$env:HARDWARE_AGENT_APPROVAL='YES'
```

The current v1 foundation does not implement real manufacturing, firmware
flashing, or physical lab execution. It only provides the shared approval gate
for future adapters.
