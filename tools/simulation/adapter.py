from __future__ import annotations

from typing import Dict


def run_open_loop_simulation(config: Dict[str, object]) -> Dict[str, object]:
    return {"status": "not_configured", "backend": config.get("backend", "unknown"), "dry_run": True}


def run_closed_loop_simulation(config: Dict[str, object]) -> Dict[str, object]:
    return {"status": "not_configured", "backend": config.get("backend", "unknown"), "dry_run": True}


def parse_waveforms(result_path: str) -> Dict[str, object]:
    return {"status": "missing", "result_path": result_path, "waveforms": {}}


def summarize_simulation_results(results: Dict[str, object]) -> str:
    return f"Simulation adapter status: {results.get('status', 'unknown')}"
