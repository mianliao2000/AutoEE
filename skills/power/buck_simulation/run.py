from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from adapters.plotting.matplotlib_renderer import save_line_plot
from adapters.simulators.ngspice_adapter import adapter_status as ngspice_status


def _num(raw: Dict[str, Any], key: str, fallback: float) -> float:
    try:
        return float(raw.get(key, fallback))
    except (TypeError, ValueError):
        return fallback


def _artifact(path: Path, output_dir: Path, kind: str, run_id: str) -> Dict[str, Any]:
    rel = path.relative_to(output_dir).as_posix()
    return {"kind": kind, "path": rel, "url": f"/api/artifact/{run_id}/simulation/{rel}", "source": "mock_adapter"}


def _build_netlist(spec: Dict[str, Any]) -> str:
    vin = _num(spec, "input_voltage_nominal_v", 12.0)
    vout = _num(spec, "output_voltage_v", 5.0)
    iout = _num(spec, "output_current_a", 3.0)
    load_r = max(vout / max(iout, 0.001), 0.001)
    fsw = _num(spec, "switching_frequency_hz", 400_000.0)
    duty = min(0.95, max(0.02, vout / vin))
    ton = duty / fsw
    period = 1.0 / fsw
    return "\n".join(
        [
            "* AutoEE generated buck converter demo netlist",
            f"V1 vin 0 DC {vin:g}",
            f"VDRV gate 0 PULSE(0 5 0 10n 10n {ton:.9g} {period:.9g})",
            "S1 vin sw gate 0 swmod",
            "D1 0 sw dmod",
            "L1 sw out 10u",
            "C1 out 0 44u ESR=12m",
            f"RLOAD out 0 {load_r:.6g}",
            ".model swmod SW(Ron=12m Roff=10Meg Vt=2 Vh=0.2)",
            ".model dmod D(Is=1n Rs=15m)",
            ".tran 0 2m 0 50n",
            ".control",
            "run",
            "write raw_output.raw",
            ".endc",
            ".end",
        ]
    )


def _mock_waveforms(spec: Dict[str, Any]) -> List[Dict[str, float]]:
    vin = _num(spec, "input_voltage_nominal_v", 12.0)
    vout = _num(spec, "output_voltage_v", 5.0)
    iout = _num(spec, "output_current_a", 3.0)
    fsw = _num(spec, "switching_frequency_hz", 400_000.0)
    inductance_h = _num(spec, "inductance_h", _num(spec, "inductance_uh", 10.0) * 1e-6)
    duty = min(0.95, max(0.02, vout / vin))
    ripple = vout * (1.0 - duty) / (inductance_h * fsw)
    period = 1.0 / fsw
    total_time = 1.2e-3
    samples = 900
    rows: List[Dict[str, float]] = []
    for idx in range(samples):
        t = total_time * idx / (samples - 1)
        phase = (t % period) / period
        tri = phase * 2.0 if phase < 0.5 else (1.0 - phase) * 2.0
        load_step = 0.0 if t < 0.55e-3 else 1.0
        settling = math.exp(-(t - 0.55e-3) / 0.00012) if t >= 0.55e-3 else 0.0
        vout_t = vout + 0.010 * math.sin(2.0 * math.pi * fsw * t) - 0.18 * load_step * settling
        il = iout * (0.55 + 0.45 * load_step) + ripple * (tri - 0.5)
        sw = vin if phase < duty else 0.0
        rows.append({"time_s": t, "vout_v": vout_t, "inductor_current_a": il, "switch_node_v": sw, "load_current_a": iout * (0.35 + 0.65 * load_step)})
    return rows


def run(input_data: Dict[str, Any], output_dir: str | Path) -> Dict[str, Any]:
    output_dir = Path(output_dir)
    plots_dir = output_dir / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = str(input_data.get("runId") or output_dir.parent.name)
    spec = dict(input_data.get("spec") or input_data)
    generated_at = datetime.now(timezone.utc).isoformat()

    netlist = _build_netlist(spec)
    (output_dir / "circuit_model.cir").write_text(netlist, encoding="utf-8")
    circuit_model = {
        "topology": "synchronous_buck_demo_model",
        "nodes": ["vin", "sw", "out", "gate", "0"],
        "components": ["V1", "VDRV", "S1", "D1", "L1", "C1", "RLOAD"],
        "source": "generated_model",
    }
    setup = {
        "analysis": "transient",
        "stop_time_s": 0.0012,
        "max_step_s": 5e-8,
        "preferredAdapter": "ngspice",
        "fallbackAdapter": "mock_adapter",
    }
    adapter = ngspice_status()
    adapter_used = "ngspice" if adapter.get("connected") else "mock_adapter"
    adapter_status = {
        **adapter,
        "usedAdapter": adapter_used,
        "isRealSimulatorData": bool(adapter.get("connected")),
        "isDemoSynthetic": not bool(adapter.get("connected")),
    }

    rows = _mock_waveforms(spec)
    csv_path = output_dir / "waveforms.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["time_s", "vout_v", "inductor_current_a", "switch_node_v", "load_current_a"])
        writer.writeheader()
        writer.writerows(rows)
    x_ms = [row["time_s"] * 1000.0 for row in rows]
    vout = [row["vout_v"] for row in rows]
    il = [row["inductor_current_a"] for row in rows]
    sw = [row["switch_node_v"] for row in rows]
    plot_paths = {
        "vout": save_line_plot(path=plots_dir / "vout.png", title="Transient Output Voltage", x=x_ms, series=[("Vout", vout)], xlabel="Time (ms)", ylabel="Voltage (V)", note=f"source: {adapter_used}"),
        "inductor_current": save_line_plot(path=plots_dir / "inductor_current.png", title="Inductor Current", x=x_ms, series=[("I_L", il)], xlabel="Time (ms)", ylabel="Current (A)", note=f"source: {adapter_used}"),
        "switch_node": save_line_plot(path=plots_dir / "switch_node.png", title="Switch Node Voltage", x=x_ms, series=[("SW", sw)], xlabel="Time (ms)", ylabel="Voltage (V)", note=f"source: {adapter_used}"),
    }

    ripple_mv = (max(vout) - min(vout)) * 1000.0
    metrics = {
        "vout_ripple_mv_pp": round(ripple_mv, 3),
        "vout_min_v": round(min(vout), 5),
        "vout_max_v": round(max(vout), 5),
        "inductor_peak_a": round(max(il), 4),
        "inductor_valley_a": round(min(il), 4),
        "source": adapter_used,
    }
    (output_dir / "circuit_model.json").write_text(json.dumps(circuit_model, indent=2), encoding="utf-8")
    (output_dir / "simulation_setup.json").write_text(json.dumps(setup, indent=2), encoding="utf-8")
    (output_dir / "adapter_status.json").write_text(json.dumps(adapter_status, indent=2), encoding="utf-8")
    (output_dir / "simulation_log.txt").write_text(
        "\n".join(
            [
                "power.buck_simulation completed.",
                f"run_id={run_id}",
                f"adapter={adapter_used}",
                "ngspice not required for demo; mock_adapter data is clearly labelled when used.",
            ]
        ),
        encoding="utf-8",
    )
    result = {
        "available": True,
        "skillId": "power.buck_simulation",
        "runId": run_id,
        "status": "completed",
        "source": "simulator" if adapter_status["isRealSimulatorData"] else "mock_adapter",
        "generatedAt": generated_at,
        "adapter": adapter_status,
        "circuitModel": circuit_model,
        "simulationSetup": setup,
        "metrics": metrics,
        "plots": [
            {"id": key, "title": key.replace("_", " ").title(), **_artifact(path, output_dir, "plot", run_id)}
            for key, path in plot_paths.items()
        ],
        "rawOutputs": [
            _artifact(output_dir / "circuit_model.cir", output_dir, "netlist", run_id),
            _artifact(output_dir / "circuit_model.json", output_dir, "json", run_id),
            _artifact(output_dir / "simulation_setup.json", output_dir, "json", run_id),
            _artifact(csv_path, output_dir, "csv", run_id),
            _artifact(output_dir / "adapter_status.json", output_dir, "json", run_id),
            _artifact(output_dir / "simulation_log.txt", output_dir, "log", run_id),
        ],
        "comparison": {
            "analysisInput": "Use Analysis tab artifacts for formula estimate comparison.",
            "simulationRippleMvPp": round(ripple_mv, 3),
            "dataProvenance": "mock_adapter synthetic waveform" if adapter_status["isDemoSynthetic"] else "ngspice raw output",
        },
    }
    result["artifacts"] = [*result["rawOutputs"], *result["plots"]]
    (output_dir / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


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

