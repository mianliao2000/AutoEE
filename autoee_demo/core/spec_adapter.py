from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

from .state import ProjectSpec


def project_spec_to_yaml_dict(spec: ProjectSpec) -> Dict[str, Any]:
    """Map the current demo ProjectSpec to the repo-level hardware spec shape."""

    output_power_w = spec.output_voltage_v * spec.output_current_a
    return {
        "project_name": spec.name,
        "application": "vehicle_industrial_usb_c_buck_charger",
        "topology": {
            "preferred": "synchronous_buck",
            "candidates": ["synchronous_buck", "asynchronous_buck"],
        },
        "input": {
            "voltage_min_v": spec.input_voltage_min_v,
            "voltage_nominal_v": spec.input_voltage_nominal_v,
            "voltage_max_v": spec.input_voltage_max_v,
        },
        "output": {
            "voltage_nominal_v": spec.output_voltage_v,
            "current_nominal_a": spec.output_current_a,
            "power_nominal_w": output_power_w,
            "power_peak_w": output_power_w,
            "tolerance_percent": spec.output_tolerance_percent,
            "ripple_mv_pp_max": spec.output_ripple_mv_pp,
        },
        "switching": {
            "frequency_target_hz": 400_000,
            "frequency_min_hz": None,
            "frequency_max_hz": None,
        },
        "efficiency": {
            "target_percent": spec.target_efficiency_percent,
            "operating_points": [
                {
                    "vin_v": spec.input_voltage_nominal_v,
                    "vout_v": spec.output_voltage_v,
                    "iout_a": spec.output_current_a,
                }
            ],
        },
        "thermal": {
            "ambient_min_c": None,
            "ambient_max_c": spec.ambient_temp_c,
            "automotive_warning_ambient_c": spec.automotive_warning_ambient_c,
            "max_junction_temp_c": 125.0,
            "max_total_loss_w": spec.max_total_loss_w,
            "cooling_method": "natural_convection_demo_assumption",
        },
        "control": {
            "closed_loop_required": True,
            "bandwidth_target_hz": None,
            "transient_requirements": [
                {
                    "load_step_a": spec.transient_step_a,
                    "max_deviation_mv": spec.transient_deviation_mv,
                    "settling_ms": spec.transient_settling_ms,
                }
            ],
        },
        "protection": {
            "over_current": True,
            "over_voltage": True,
            "under_voltage": True,
            "over_temperature": True,
        },
        "manufacturing": {
            "preferred_vendor": None,
            "assembly_required": False,
            "max_bom_cost_usd": None,
        },
        "vendors": {"component_distributors": ["DigiKey", "Mouser", "LCSC"]},
        "testing": {
            "operating_points": [
                {"vin_v": 9.0, "iout_a": 0.3},
                {"vin_v": 12.0, "iout_a": 3.0},
                {"vin_v": 24.0, "iout_a": 3.0},
                {"vin_v": 36.0, "iout_a": 3.0},
            ],
            "required_reports": ["design_review", "eval_summary"],
        },
        "safety": {
            "human_approval_required_for": [
                "manufacturing_order",
                "firmware_flash",
                "high_voltage_test",
                "high_current_test",
                "final_power_device_selection",
            ]
        },
        "assumptions": [
            "Default demo uses mock component catalog and synthetic simulation when external tools are not configured.",
            "Thermal estimates are first-order and require human signoff before hardware release.",
        ],
        "open_questions": [
            "Target enclosure volume and allowed maximum height are not defined.",
            "Final USB-C controller, protection, and communication requirements are not defined.",
        ],
    }


def project_spec_from_yaml_dict(raw: Dict[str, Any]) -> ProjectSpec:
    """Load the supported YAML hardware spec fields back into ProjectSpec."""

    input_section = dict(raw.get("input", {}) or {})
    output_section = dict(raw.get("output", {}) or {})
    efficiency = dict(raw.get("efficiency", {}) or {})
    thermal = dict(raw.get("thermal", {}) or {})
    control = dict(raw.get("control", {}) or {})
    transient = {}
    transient_requirements = control.get("transient_requirements") or []
    if transient_requirements and isinstance(transient_requirements[0], dict):
        transient = dict(transient_requirements[0])

    return ProjectSpec(
        name=str(raw.get("project_name") or ProjectSpec().name),
        input_voltage_min_v=float(input_section.get("voltage_min_v") or ProjectSpec().input_voltage_min_v),
        input_voltage_nominal_v=float(input_section.get("voltage_nominal_v") or ProjectSpec().input_voltage_nominal_v),
        input_voltage_max_v=float(input_section.get("voltage_max_v") or ProjectSpec().input_voltage_max_v),
        output_voltage_v=float(output_section.get("voltage_nominal_v") or ProjectSpec().output_voltage_v),
        output_current_a=float(output_section.get("current_nominal_a") or ProjectSpec().output_current_a),
        output_ripple_mv_pp=float(output_section.get("ripple_mv_pp_max") or ProjectSpec().output_ripple_mv_pp),
        transient_step_a=float(transient.get("load_step_a") or ProjectSpec().transient_step_a),
        transient_deviation_mv=float(transient.get("max_deviation_mv") or ProjectSpec().transient_deviation_mv),
        target_efficiency_percent=float(efficiency.get("target_percent") or ProjectSpec().target_efficiency_percent),
        ambient_temp_c=float(thermal.get("ambient_max_c") or ProjectSpec().ambient_temp_c),
        automotive_warning_ambient_c=float(
            thermal.get("automotive_warning_ambient_c") or ProjectSpec().automotive_warning_ambient_c
        ),
        output_tolerance_percent=float(output_section.get("tolerance_percent") or ProjectSpec().output_tolerance_percent),
        transient_settling_ms=float(transient.get("settling_ms") or ProjectSpec().transient_settling_ms),
        max_total_loss_w=float(thermal.get("max_total_loss_w") or ProjectSpec().max_total_loss_w),
    )


def save_project_spec_yaml(spec: ProjectSpec, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(project_spec_to_yaml_dict(spec), sort_keys=False), encoding="utf-8")
    return path


def load_project_spec_yaml(path: Path) -> ProjectSpec:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Spec YAML must contain a mapping: {path}")
    return project_spec_from_yaml_dict(raw)
