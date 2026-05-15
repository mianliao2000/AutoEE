from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ProjectSpec:
    """High-level specs every AI-assisted workflow step receives."""

    name: str = "AutoEE 15W USB-C Buck Charger Demo"
    input_voltage_min_v: float = 9.0
    input_voltage_nominal_v: float = 12.0
    input_voltage_max_v: float = 36.0
    output_voltage_v: float = 5.0
    output_current_a: float = 3.0
    output_ripple_mv_pp: float = 50.0
    transient_step_a: float = 2.7
    transient_deviation_mv: float = 250.0
    target_efficiency_percent: float = 90.0
    ambient_temp_c: float = 60.0
    automotive_warning_ambient_c: float = 85.0
    output_tolerance_percent: float = 5.0
    transient_settling_ms: float = 1.0
    max_total_loss_w: float = 1.7

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "ProjectSpec":
        allowed = set(cls().__dataclass_fields__.keys())
        return cls(**{key: value for key, value in raw.items() if key in allowed})


@dataclass
class DesignCandidate:
    topology: str
    switching_frequency_hz: float
    inductor_uh: float
    output_cap_uf: float
    input_cap_uf: float
    duty_nominal: float
    source: str = "deterministic_estimate"
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PartCandidate:
    category: str
    mpn: str
    manufacturer: str
    key_params: Dict[str, Any]
    unit_price_usd: float
    stock_qty: int
    footprint: str
    datasheet_url: str = ""
    source: str = "mock_catalog"
    quantity: int = 1
    supplier_links: Dict[str, str] = field(default_factory=dict)
    compliance: str = "meets_demo_requirements"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["line_total_usd"] = round(float(self.unit_price_usd) * int(self.quantity), 4)
        return data


@dataclass
class BomSelection:
    high_side_mosfet: PartCandidate
    low_side_mosfet: PartCandidate
    inductor: PartCandidate
    input_capacitor: PartCandidate
    output_capacitor: PartCandidate
    source: str = "mock_catalog"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "high_side_mosfet": self.high_side_mosfet.to_dict(),
            "low_side_mosfet": self.low_side_mosfet.to_dict(),
            "inductor": self.inductor.to_dict(),
            "input_capacitor": self.input_capacitor.to_dict(),
            "output_capacitor": self.output_capacitor.to_dict(),
            "source": self.source,
        }


@dataclass
class LossBreakdown:
    items_w: Dict[str, float]
    total_loss_w: float
    output_power_w: float
    input_power_w: float
    efficiency_percent: float
    confidence: str = "medium"
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ThermalResult:
    component_temps_c: Dict[str, float]
    max_junction_temp_c: float
    warnings: List[str]
    model_notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SimulationResult:
    backend: str
    metrics: Dict[str, float]
    waveforms: Dict[str, List[float]]
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ControlResult:
    kp: float
    ki: float
    kd: float
    kf: float
    crossover_hz: float
    phase_margin_deg: float
    metrics: Dict[str, float]
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProgressEvent:
    module_id: str
    status: str
    message: str
    timestamp: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ArtifactRef:
    """Reference to a generated artifact without embedding large content."""

    kind: str
    path: str
    created_at: str = field(default_factory=utc_now_iso)
    source: str = "generated"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "path": self.path,
            "created_at": self.created_at,
            "source": self.source,
        }


@dataclass
class DesignState:
    """Serializable project memory passed to deterministic modules and LLMs."""

    spec: ProjectSpec = field(default_factory=ProjectSpec)
    workflow_status: str = "idle"
    deterministic_results: Dict[str, Any] = field(default_factory=dict)
    ai_notes: Dict[str, str] = field(default_factory=dict)
    module_status: Dict[str, str] = field(default_factory=dict)
    progress_events: List[ProgressEvent] = field(default_factory=list)
    artifacts: List[ArtifactRef] = field(default_factory=list)
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "spec": self.spec.to_dict(),
            "workflow_status": self.workflow_status,
            "deterministic_results": self.deterministic_results,
            "ai_notes": self.ai_notes,
            "module_status": self.module_status,
            "progress_events": [event.to_dict() for event in self.progress_events],
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "DesignState":
        state = cls(spec=ProjectSpec.from_dict(dict(raw.get("spec", {}))))
        state.workflow_status = str(raw.get("workflow_status", "idle"))
        state.deterministic_results = dict(raw.get("deterministic_results", {}))
        state.ai_notes = dict(raw.get("ai_notes", {}))
        state.module_status = dict(raw.get("module_status", {}))
        state.progress_events = [
            ProgressEvent(
                module_id=str(item.get("module_id", "")),
                status=str(item.get("status", "")),
                message=str(item.get("message", "")),
                timestamp=str(item.get("timestamp", utc_now_iso())),
            )
            for item in raw.get("progress_events", [])
        ]
        state.artifacts = [
            ArtifactRef(
                kind=str(item.get("kind", "")),
                path=str(item.get("path", "")),
                created_at=str(item.get("created_at", utc_now_iso())),
                source=str(item.get("source", "generated")),
            )
            for item in raw.get("artifacts", [])
        ]
        state.updated_at = str(raw.get("updated_at", utc_now_iso()))
        return state

    def record_event(self, module_id: str, status: str, message: str) -> None:
        self.module_status[module_id] = status
        self.progress_events.append(ProgressEvent(module_id=module_id, status=status, message=message))
        self.updated_at = utc_now_iso()

    def set_result(self, module_id: str, result: Dict[str, Any], summary: str = "") -> None:
        self.deterministic_results[module_id] = result
        if summary:
            self.ai_notes.setdefault(module_id, summary)
        self.record_event(module_id, "complete", summary or "Module completed.")

    def clear_from(self, module_ids: List[str]) -> None:
        for module_id in module_ids:
            self.deterministic_results.pop(module_id, None)
            self.ai_notes.pop(module_id, None)
            self.module_status.pop(module_id, None)
        self.workflow_status = "edited"
        self.updated_at = utc_now_iso()

    def save_json(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return path

    @classmethod
    def load_json(cls, path: Path) -> "DesignState":
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def model_context_payload(self) -> Dict[str, Any]:
        """Compact payload sent to a model backend for step-level reasoning."""

        return {
            "project_spec": self.spec.to_dict(),
            "design_state": {
                "workflow_status": self.workflow_status,
                "deterministic_results": self.deterministic_results,
                "artifact_count": len(self.artifacts),
            },
            "policy": {
                "llm_role": "explain, summarize, draft candidates, and extract datasheet fields",
                "deterministic_boundary": (
                    "Do not override equations, losses, thermal values, simulation metrics, "
                    "or other deterministic module outputs."
                ),
                "source_policy": "Cite datasheets or mark statements as assumptions when sources are absent.",
            },
        }


def safe_get_result(state: DesignState, module_id: str) -> Dict[str, Any]:
    value = state.deterministic_results.get(module_id, {})
    return value if isinstance(value, dict) else {}


def get_selected_candidate(state: DesignState) -> Optional[Dict[str, Any]]:
    result = safe_get_result(state, "spec_analyzer")
    candidate = result.get("selected_candidate")
    return candidate if isinstance(candidate, dict) else None
