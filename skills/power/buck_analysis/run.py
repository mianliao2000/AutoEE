from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from adapters.plotting.matplotlib_renderer import save_bar_plot, save_line_plot
from adapters.reports.latex_report_builder import write_equation_bundle


def _num(raw: Dict[str, Any], key: str, fallback: float) -> float:
    try:
        return float(raw.get(key, fallback))
    except (TypeError, ValueError):
        return fallback


def _round(value: float, digits: int = 4) -> float:
    return round(float(value), digits)


def _artifact(path: Path, output_dir: Path, kind: str, run_id: str) -> Dict[str, Any]:
    rel = path.relative_to(output_dir).as_posix()
    return {"kind": kind, "path": rel, "url": f"/api/artifact/{run_id}/analysis/{rel}", "source": "analysis_formula"}


def _triangular(time_s: List[float], period_s: float, low: float, high: float) -> List[float]:
    values = []
    span = high - low
    for t in time_s:
        phase = (t % period_s) / period_s
        if phase < 0.5:
            values.append(low + span * phase * 2.0)
        else:
            values.append(high - span * (phase - 0.5) * 2.0)
    return values


def run(input_data: Dict[str, Any], output_dir: str | Path) -> Dict[str, Any]:
    output_dir = Path(output_dir)
    plots_dir = output_dir / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = str(input_data.get("runId") or output_dir.parent.name)
    spec = dict(input_data.get("spec") or input_data)

    vin_min = _num(spec, "input_voltage_min_v", _num(spec, "vin_min", 9.0))
    vin_nom = _num(spec, "input_voltage_nominal_v", _num(spec, "vin_nom", 12.0))
    vin_max = _num(spec, "input_voltage_max_v", _num(spec, "vin_max", 36.0))
    vout = _num(spec, "output_voltage_v", _num(spec, "vout", 5.0))
    iout = _num(spec, "output_current_a", _num(spec, "iout", 3.0))
    fsw = _num(spec, "switching_frequency_hz", _num(spec, "f_sw", 400_000.0))
    inductance_h = _num(spec, "inductance_h", _num(spec, "inductance_uh", 10.0) * 1e-6)
    efficiency_target = _num(spec, "target_efficiency_percent", 90.0) / 100.0
    cout_f = _num(spec, "output_cap_f", _num(spec, "output_cap_uf", 44.0) * 1e-6)
    esr_ohm = _num(spec, "output_cap_esr_ohm", 0.012)
    inductor_dcr_ohm = _num(spec, "inductor_dcr_ohm", 0.018)
    mosfet_rds_on_ohm = _num(spec, "mosfet_rds_on_ohm", 0.018)
    edge_time_s = _num(spec, "switch_edge_time_ns", 12.0) * 1e-9
    thermal_rise_c_per_w = _num(spec, "thermal_rise_c_per_w", 34.0)
    ambient_c = _num(spec, "ambient_temp_c", 60.0)

    vin_values = [vin_min, vin_nom, vin_max]
    p_out = vout * iout
    rows = []
    ripple_values = []
    duty_values = []
    for vin in vin_values:
        duty = min(0.98, max(0.02, vout / vin))
        ripple = vout * (1.0 - duty) / (inductance_h * fsw)
        i_peak = iout + ripple / 2.0
        input_current = p_out / max(vin * efficiency_target, 1e-9)
        rows.append(
            {
                "vin_v": _round(vin, 3),
                "duty": _round(duty, 5),
                "input_current_a": _round(input_current, 4),
                "inductor_ripple_a": _round(ripple, 4),
                "inductor_peak_a": _round(i_peak, 4),
                "capacitor_ripple_mv_pp": _round((ripple / (8.0 * fsw * cout_f) + ripple * esr_ohm) * 1000.0, 3),
            }
        )
        duty_values.append(duty)
        ripple_values.append(ripple)

    nominal = rows[1] if len(rows) > 1 else rows[0]
    rms_current_est = math.sqrt(iout**2 + (nominal["inductor_ripple_a"] ** 2) / 12.0)
    conduction_loss_w = rms_current_est**2 * mosfet_rds_on_ohm
    switching_loss_w = 0.5 * vin_nom * iout * edge_time_s * fsw * 2.0
    dcr_loss_w = rms_current_est**2 * inductor_dcr_ohm
    cap_esr_loss_w = (nominal["inductor_ripple_a"] / math.sqrt(12.0)) ** 2 * esr_ohm
    estimated_loss_w = conduction_loss_w + switching_loss_w + dcr_loss_w + cap_esr_loss_w
    estimated_efficiency = p_out / (p_out + estimated_loss_w) if p_out > 0 else 0.0
    hot_spot_c = ambient_c + estimated_loss_w * thermal_rise_c_per_w

    equations = [
        {"id": "pout", "label": "Output power", "latex": r"P_{out}=V_{out}I_{out}"},
        {"id": "duty", "label": "Duty cycle estimate", "latex": r"D \approx \frac{V_{out}}{V_{in}}"},
        {"id": "ripple", "label": "Inductor ripple current", "latex": r"\Delta I_L \approx \frac{V_{out}(1-D)}{L f_{sw}}"},
        {"id": "ipeak", "label": "Peak inductor current", "latex": r"I_{L,pk}=I_{out}+\frac{\Delta I_L}{2}"},
        {"id": "cap_ripple", "label": "Capacitor ripple estimate", "latex": r"\Delta V_{out} \approx \frac{\Delta I_L}{8 f_{sw} C_{out}}+\Delta I_L ESR"},
        {"id": "dcr_loss", "label": "Inductor DCR loss", "latex": r"P_{DCR}\approx I_{L,rms}^{2}R_{DCR}"},
    ]

    period = 1.0 / fsw
    samples = 220
    time_s = [idx * period * 4.0 / (samples - 1) for idx in range(samples)]
    il = _triangular(time_s, period, iout - nominal["inductor_ripple_a"] / 2.0, iout + nominal["inductor_ripple_a"] / 2.0)
    switch_v = [vin_nom if (t % period) / period < nominal["duty"] else 0.0 for t in time_s]

    plot_paths = {
        "inductor_current": save_line_plot(path=plots_dir / "inductor_current.png", title="Idealized Inductor Current", x=[t * 1e6 for t in time_s], series=[("I_L", il)], xlabel="Time (us)", ylabel="Current (A)", note="source: analysis_formula"),
        "switch_node": save_line_plot(path=plots_dir / "switch_node.png", title="Idealized Switch Node", x=[t * 1e6 for t in time_s], series=[("SW", switch_v)], xlabel="Time (us)", ylabel="Voltage (V)", note="source: analysis_formula"),
        "duty_vs_vin": save_line_plot(path=plots_dir / "duty_vs_vin.png", title="Duty Cycle vs Input Voltage", x=vin_values, series=[("D", duty_values)], xlabel="Input Voltage (V)", ylabel="Duty Cycle", note="source: analysis_formula"),
        "ripple_vs_vin": save_line_plot(path=plots_dir / "ripple_vs_vin.png", title="Ripple Current vs Input Voltage", x=vin_values, series=[("Delta I_L", ripple_values)], xlabel="Input Voltage (V)", ylabel="Ripple Current (A)", note="source: analysis_formula"),
        "loss_breakdown": save_bar_plot(path=plots_dir / "loss_breakdown.png", title="First-Order Loss Breakdown", labels=["FET cond.", "Switching", "Inductor DCR", "Cap ESR"], values=[conduction_loss_w, switching_loss_w, dcr_loss_w, cap_esr_loss_w], ylabel="Loss (W)", note="source: analysis_formula"),
    }

    generated_at = datetime.now(timezone.utc).isoformat()
    assumptions = {
        "vin_min_v": vin_min,
        "vin_nom_v": vin_nom,
        "vin_max_v": vin_max,
        "vout_v": vout,
        "iout_a": iout,
        "switching_frequency_hz": fsw,
        "inductance_h": inductance_h,
        "output_cap_f": cout_f,
        "efficiency_target": efficiency_target,
        "mosfet_rds_on_ohm": mosfet_rds_on_ohm,
        "inductor_dcr_ohm": inductor_dcr_ohm,
        "output_cap_esr_ohm": esr_ohm,
        "source": "demo assumptions; not signoff",
    }
    results = {
        "available": True,
        "skillId": "power.buck_analysis",
        "runId": run_id,
        "status": "completed",
        "source": "analysis_formula",
        "generatedAt": generated_at,
        "inputHash": f"{vin_min:g}-{vin_nom:g}-{vin_max:g}-{vout:g}-{iout:g}-{fsw:g}-{inductance_h:g}",
        "summary": {
            "output_power_w": _round(p_out, 4),
            "estimated_efficiency_percent": _round(estimated_efficiency * 100.0, 3),
            "estimated_loss_w": _round(estimated_loss_w, 4),
            "hot_spot_estimate_c": _round(hot_spot_c, 2),
            "model": "first_order_buck_converter",
        },
        "assumptions": assumptions,
        "equations": equations,
        "numericalResults": rows,
        "lossBreakdown": [
            {"label": "MOSFET conduction", "value_w": _round(conduction_loss_w, 5)},
            {"label": "Switching overlap", "value_w": _round(switching_loss_w, 5)},
            {"label": "Inductor DCR", "value_w": _round(dcr_loss_w, 5)},
            {"label": "Output capacitor ESR", "value_w": _round(cap_esr_loss_w, 5)},
        ],
        "risksAndLimits": [
            "First-order CCM buck estimate; does not replace SPICE, PLECS, SIMPLIS, EMI, or thermal signoff.",
            "Switching loss assumes fixed edge time and ignores reverse recovery, gate drive, and layout parasitics.",
            "Capacitor DC bias and inductor saturation must be verified with selected datasheets.",
        ],
        "plots": [
            {"id": key, "title": key.replace("_", " ").title(), **_artifact(path, output_dir, "plot", run_id)}
            for key, path in plot_paths.items()
        ],
        "artifacts": [],
    }
    (output_dir / "assumptions.json").write_text(json.dumps(assumptions, indent=2), encoding="utf-8")
    write_equation_bundle(output_dir / "equations.tex", equations)
    (output_dir / "analysis_log.txt").write_text(
        "\n".join(
            [
                "power.buck_analysis completed.",
                f"run_id={run_id}",
                f"source=analysis_formula generated_at={generated_at}",
                "Matplotlib plots saved under plots/.",
            ]
        ),
        encoding="utf-8",
    )
    results["artifacts"] = [
        _artifact(output_dir / "results.json", output_dir, "json", run_id),
        _artifact(output_dir / "assumptions.json", output_dir, "json", run_id),
        _artifact(output_dir / "equations.tex", output_dir, "latex", run_id),
        _artifact(output_dir / "analysis_log.txt", output_dir, "log", run_id),
        *results["plots"],
    ]
    (output_dir / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = run(payload, args.output_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

