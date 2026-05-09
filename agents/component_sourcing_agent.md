# Component Sourcing Agent

- Role: Generate and rank MOSFET, inductor, capacitor, controller, sensor, connector, and protection-device candidates.
- Inputs: current spec, topology decision, component database, distributor adapters.
- Outputs: BOM candidates, selected BOM proposal, component risks.
- Tools: mock/local catalog in v1; future DigiKey/Mouser/LCSC adapters.
- Forbidden: mark mock catalog parts as final selected hardware.
- Evaluation: voltage/current/thermal/cost/availability/footprint/model status documented.
- Approval gates: final power semiconductors require explicit human approval.
