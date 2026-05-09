# Skill: Rough Loss Estimation

Use for fast feasibility screening before detailed simulation.

Inputs:
- Spec, selected BOM, operating point, topology assumptions.

Steps:
- Estimate MOSFET conduction, switching, gate-drive, Coss/Eoss, body-diode/deadtime, reverse-recovery placeholder, inductor DCR/core, capacitor ESR, and PDN loss.
- Iterate temperature-sensitive Rds_on and DCR if data exists.
- Mark missing datasheet fields.

Checks:
- Do not treat rough estimates as signoff data.
