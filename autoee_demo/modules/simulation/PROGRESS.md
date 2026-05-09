# Simulation Progress

## Final Goal
- Run PLECS/LTspice simulations and compare waveforms against deterministic loss and ripple estimates.

## Completed
- Synthetic waveform backend for offline workflow validation.
- Expanded waveform schema with `load_current_a`, `duty_command`, `limit_bands`, `events`, source badge, and signoff status while preserving legacy `time_us`, `vout_v`, `il_a`, and `switch_v`.
- Improved the synthetic Buck waveform shape: switch node uses PWM high/low states, inductor current uses piecewise triangular ripple around the load-current operating point, and output voltage is updated through output-capacitor current with ESR plus a load-step recovery term.
- Current offline demo metrics are Vout ripple 3.21 mVpp, load-step transient 199.05 mV, and IL peak 3.394 A for the 5V/3A charger spec.

## Verification
- Unit tests confirm waveform lab fields exist and align with sample count.
- Unit tests assert the load step, switch-node span, and inductor peak behavior are present.

## Next Steps
- Add PLECS XML-RPC and LTspice adapters behind the same interface.
- Replace the synthetic recovery term with real control-loop simulation once the PLECS/LTspice backend is configured.
