from __future__ import annotations

from typing import Dict


def run_magnetics_extraction(config: Dict[str, object]) -> Dict[str, object]:
    return {"status": "not_configured", "dry_run": True, "config": config}


def run_parasitic_extraction(config: Dict[str, object]) -> Dict[str, object]:
    return {"status": "not_configured", "dry_run": True, "config": config}


def parse_em_results(result_path: str) -> Dict[str, object]:
    return {"status": "missing", "result_path": result_path, "metrics": {}}
