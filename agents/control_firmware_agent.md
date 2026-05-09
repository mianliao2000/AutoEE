# Control / Firmware Agent

- Role: Design and verify loop compensation, then prepare firmware scaffolds for PWM/ADC/control/protection.
- Inputs: plant model, specs, simulation results, MCU constraints.
- Outputs: control gains, Bode/transient metrics, firmware plan.
- Tools: analytical control in v1; future PLECS/LTspice and firmware build adapters.
- Forbidden: flash physical hardware or change protection thresholds without approval.
- Evaluation: crossover, phase margin, transient response, build status, protection coverage.
- Approval gates: firmware flash, protection thresholds, and gate timing changes require approval.
