# AutoEE Approval Gates

The following actions require explicit mechanical approval before real execution:

1. Submitting PCB or PCBA orders.
2. Exporting a production-ready manufacturing package.
3. Flashing firmware to physical hardware.
4. Running high-voltage lab tests.
5. Running high-current lab tests.
6. Changing protection thresholds.
7. Changing deadtime or gate-driver timing.
8. Bypassing DRC/ERC failures.
9. Selecting final power semiconductors.
10. Changing isolation assumptions.
11. Changing creepage/clearance constraints.
12. Marking a design as validated.
13. Marking a design as production-ready.

Approval must be explicit and mechanical, such as `--approve` or
`HARDWARE_AGENT_APPROVAL=YES`. Natural-language chat approval is not enough.
