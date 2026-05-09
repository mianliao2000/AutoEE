# Skill: PCB Power Layout Check

Use when reviewing high-current or high-dv/dt PCB layouts.

Inputs:
- PCB layout, schematic, current path, switching node, gate driver, sense routing.

Steps:
- Review hot-loop area, gate-loop routing, current density, thermal vias, Kelvin sensing, creepage/clearance, and return paths.
- Run DRC/ERC where available.

Human approval:
- Required to bypass DRC/ERC or mark production-ready.
