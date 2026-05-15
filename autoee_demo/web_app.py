from __future__ import annotations

import asyncio
import json
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from autoee_demo.core import AutoEEAgent, DesignState, ProjectSpec
from autoee_demo.model_backend import MemorySecretStore, ModelBackendSettings, ModelManager
from autoee_demo.web_state import build_investor_snapshot_markdown, build_web_state


def runtime_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def find_static_dir() -> Optional[Path]:
    package_static = Path(__file__).resolve().parent / "web_static"
    repo_static = Path(__file__).resolve().parents[1] / "web" / "dist"
    for candidate in [package_static, repo_static]:
        if (candidate / "index.html").exists():
            return candidate
    return None


class WebDemoSession:
    """Thread-safe-ish state holder for the local web demo server."""

    def __init__(
        self,
        min_module_seconds: float = 0.5,
        output_root: Optional[Path] = None,
    ):
        self.lock = threading.RLock()
        self.min_module_seconds = float(min_module_seconds)
        self.output_root = Path(output_root) if output_root else runtime_base_dir() / "results" / "web_runs"
        self.version = 0
        self.running = False
        self.stop_requested = False
        self.started_at: Optional[float] = None
        self.presentation_status: Dict[str, str] = {}
        self.agent = self._new_agent()

    @staticmethod
    def _new_agent() -> AutoEEAgent:
        settings = ModelBackendSettings(default_provider="mock")
        manager = ModelManager(settings=settings, secret_store=MemorySecretStore())
        return AutoEEAgent(state=DesignState(), model_manager=manager)

    def _bump(self) -> None:
        self.version += 1

    def state_payload(self) -> Dict[str, Any]:
        with self.lock:
            return build_web_state(
                self.agent.state,
                presentation_status=dict(self.presentation_status),
                running=self.running,
                started_at=self.started_at,
            )

    def reset(self) -> Dict[str, Any]:
        with self.lock:
            spec = self.agent.state.spec
            self.agent = self._new_agent()
            self.agent.state = DesignState(spec=spec)
            self.presentation_status.clear()
            self.running = False
            self.stop_requested = False
            self.started_at = None
            self.agent.state.record_event("ui", "reset", "Web demo reset while preserving default specs.")
            self._bump()
        return self.state_payload()

    def update_spec(self, raw_spec: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            if self.running:
                raise RuntimeError("Cannot edit specs while the demo is running.")
            merged = self.agent.state.spec.to_dict()
            merged.update(raw_spec)
            spec = ProjectSpec.from_dict(merged)
            self._validate_spec(spec)
            self.agent = self._new_agent()
            self.agent.state = DesignState(spec=spec)
            self.presentation_status.clear()
            self.stop_requested = False
            self.started_at = None
            self.agent.state.workflow_status = "edited"
            self.agent.state.record_event("spec", "edited", "Design specs updated; previous results were cleared.")
            self._bump()
        return self.state_payload()

    @staticmethod
    def _validate_spec(spec: ProjectSpec) -> None:
        if not spec.name.strip():
            raise ValueError("Project name is required.")
        if not (spec.input_voltage_min_v > 0 and spec.input_voltage_nominal_v > 0 and spec.input_voltage_max_v > 0):
            raise ValueError("Input voltages must be positive.")
        if not (spec.input_voltage_min_v <= spec.input_voltage_nominal_v <= spec.input_voltage_max_v):
            raise ValueError("Input voltage must satisfy Vin min <= Vin nominal <= Vin max.")
        positive_fields = {
            "Vout": spec.output_voltage_v,
            "Iout": spec.output_current_a,
            "Ripple": spec.output_ripple_mv_pp,
            "Transient step": spec.transient_step_a,
            "Transient deviation": spec.transient_deviation_mv,
            "Efficiency target": spec.target_efficiency_percent,
            "Ambient temperature": spec.ambient_temp_c,
            "Loss max": spec.max_total_loss_w,
        }
        invalid = [name for name, value in positive_fields.items() if value <= 0]
        if invalid:
            raise ValueError(f"Spec values must be positive: {', '.join(invalid)}.")

    def stop(self) -> Dict[str, Any]:
        with self.lock:
            self.stop_requested = True
            if self.running:
                self.agent.stop()
            self._bump()
        return self.state_payload()

    def run_demo(self) -> bool:
        with self.lock:
            if self.running:
                return False
            self.running = True
            self.stop_requested = False
            self.started_at = time.monotonic()
            self.presentation_status.clear()
            self.agent.stop_requested = False
            self.agent.state.workflow_status = "running"
            self.agent.state.record_event("agent", "running", "Web investor demo started.")
            self._bump()
        worker = threading.Thread(target=self._run_demo_thread, name="AutoEEWebDemoRunner", daemon=True)
        worker.start()
        return True

    def _run_demo_thread(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = self.output_root / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)
        try:
            for skill in self.agent.skills:
                with self.lock:
                    if self.stop_requested:
                        break
                    self.presentation_status[skill.module_id] = "running"
                    self.agent.state.record_event(skill.module_id, "running", "Web demo module is running.")
                    self._bump()

                start = time.monotonic()
                try:
                    self.agent.run_skill(skill.module_id, output_dir=run_dir)
                except Exception as exc:  # pragma: no cover - exercised by manual adapters more than unit tests
                    with self.lock:
                        self.presentation_status.pop(skill.module_id, None)
                        self.agent.state.record_event(skill.module_id, "error", f"{type(exc).__name__}: {exc}")
                        self.agent.state.workflow_status = "error"
                        self._bump()
                    break

                while time.monotonic() - start < self.min_module_seconds:
                    with self.lock:
                        if self.stop_requested:
                            break
                    time.sleep(0.05)

                with self.lock:
                    self.presentation_status.pop(skill.module_id, None)
                    self._bump()
                    if self.stop_requested:
                        break

            with self.lock:
                if self.stop_requested:
                    self.agent.state.workflow_status = "stopped"
                    self.agent.state.record_event("agent", "stopped", "Web investor demo stopped by user.")
                elif self.agent.state.workflow_status != "error":
                    self.agent.state.workflow_status = "complete"
                    self.agent.state.record_event("agent", "complete", "Web investor demo completed.")
        finally:
            with self.lock:
                self.running = False
                self.presentation_status.clear()
                self._bump()

    def export_snapshot(self) -> Dict[str, Any]:
        snapshot_dir = self.output_root.parent / "investor_snapshots"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        path = snapshot_dir / f"autoee_investor_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with self.lock:
            text = build_investor_snapshot_markdown(self.agent.state)
        path.write_text(text, encoding="utf-8")
        with self.lock:
            self.agent.state.record_event("export", "complete", f"Investor snapshot exported to {path}.")
            self._bump()
        return {"ok": True, "path": str(path)}


def create_app(session: Optional[WebDemoSession] = None) -> FastAPI:
    app = FastAPI(title="AutoEE Hardware Agent", docs_url=None, redoc_url=None)
    app.state.session = session or WebDemoSession()

    @app.get("/api/state")
    def get_state() -> JSONResponse:
        return JSONResponse(app.state.session.state_payload())

    @app.post("/api/run-demo")
    def run_demo() -> JSONResponse:
        started = app.state.session.run_demo()
        return JSONResponse({"ok": True, "started": started, "state": app.state.session.state_payload()})

    @app.post("/api/stop")
    def stop() -> JSONResponse:
        return JSONResponse({"ok": True, "state": app.state.session.stop()})

    @app.post("/api/reset")
    def reset() -> JSONResponse:
        return JSONResponse({"ok": True, "state": app.state.session.reset()})

    @app.post("/api/spec")
    def update_spec(payload: Dict[str, Any]) -> JSONResponse:
        spec_payload = payload.get("spec", payload)
        if not isinstance(spec_payload, dict):
            raise HTTPException(status_code=400, detail="Expected JSON object with a spec field.")
        try:
            state = app.state.session.update_spec(spec_payload)
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return JSONResponse({"ok": True, "state": state})

    @app.post("/api/export-snapshot")
    def export_snapshot() -> JSONResponse:
        result = app.state.session.export_snapshot()
        result["state"] = app.state.session.state_payload()
        return JSONResponse(result)

    @app.get("/api/events")
    async def events() -> StreamingResponse:
        async def stream():
            last_version = -1
            while True:
                session_obj: WebDemoSession = app.state.session
                with session_obj.lock:
                    version = session_obj.version
                if version != last_version:
                    last_version = version
                    payload = session_obj.state_payload()
                    yield f"event: state\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                else:
                    yield ": keepalive\n\n"
                await asyncio.sleep(0.25)

        return StreamingResponse(stream(), media_type="text/event-stream")

    static_dir = find_static_dir()
    if static_dir:
        assets_dir = static_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{full_path:path}")
        def spa(full_path: str = ""):
            target = static_dir / full_path
            if full_path and target.exists() and target.is_file():
                return FileResponse(target)
            return FileResponse(static_dir / "index.html")

    else:

        @app.get("/{full_path:path}")
        def no_frontend(full_path: str = "") -> HTMLResponse:
            return HTMLResponse(
                """
                <html>
                  <head><title>AutoEE Hardware Agent</title></head>
                  <body style="font-family:Arial, sans-serif; padding:40px;">
                    <h1>AutoEE Hardware Agent API is running.</h1>
                    <p>The polished web frontend has not been built yet.</p>
                    <p>Run <code>npm --prefix web install</code> and <code>npm --prefix web run build</code>, then restart.</p>
                    <p>State API: <a href="/api/state">/api/state</a></p>
                  </body>
                </html>
                """
            )

    return app
