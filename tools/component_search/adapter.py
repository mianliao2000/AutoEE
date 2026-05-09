from __future__ import annotations

from typing import Dict, List, Optional


def search_components(query: str, constraints: Dict[str, object]) -> List[Dict[str, object]]:
    return [{"status": "not_configured", "query": query, "constraints": constraints, "source": "adapter_stub"}]


def get_component_details(part_number: str, vendor: Optional[str] = None) -> Dict[str, object]:
    return {"status": "not_configured", "part_number": part_number, "vendor": vendor, "source": "adapter_stub"}


def rank_components(candidates: List[Dict[str, object]], metrics: Dict[str, object]) -> List[Dict[str, object]]:
    return [{**candidate, "ranking_status": "unranked_adapter_stub", "metrics": metrics} for candidate in candidates]
