# Skill: Open-Loop Simulation Check

Use after generating open-loop Buck waveforms.

Inputs:
- Vout, inductor current, switch node, operating point, expected ripple.

Steps:
- Verify duty, current ripple, peak/valley current, switch-node state, and output ripple.
- Compare simulation metrics to deterministic estimates.
- Mark synthetic waveforms as non-signoff.

Checks:
- Export waveform files for future regression.
