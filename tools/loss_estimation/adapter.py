from __future__ import annotations

from typing import Dict, List


def estimate_mosfet_loss(device: Dict[str, object], operating_point: Dict[str, object]) -> Dict[str, object]:
    return {"status": "not_configured", "device": device.get("mpn"), "operating_point": operating_point}


def estimate_capacitor_loss(capacitor: Dict[str, object], ripple_current: float) -> Dict[str, object]:
    return {"status": "not_configured", "capacitor": capacitor.get("mpn"), "ripple_current_a": ripple_current}


def estimate_inductor_loss(inductor: Dict[str, object], waveform: Dict[str, object]) -> Dict[str, object]:
    return {"status": "not_configured", "inductor": inductor.get("mpn"), "waveform": waveform}


def estimate_total_loss(bom: List[Dict[str, object]], operating_points: List[Dict[str, object]]) -> Dict[str, object]:
    return {"status": "not_configured", "bom_count": len(bom), "operating_points": operating_points}
