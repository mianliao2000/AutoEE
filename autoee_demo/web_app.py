from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from autoee_demo.core import AutoEEAgent, DesignState, ProjectSpec
from autoee_demo.model_backend import MemorySecretStore, ModelBackendSettings, ModelManager, ProviderConfig
from autoee_demo.project_store import ProjectRepository, project_db_path
from autoee_demo.skill_runner import run_local_skill
from autoee_demo.web_state import build_web_state


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


def dotenv_candidates() -> List[Path]:
    repo_root = Path(__file__).resolve().parents[1]
    return [
        runtime_base_dir() / ".env",
        repo_root / ".env",
    ]


def load_dotenv_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_autoee_env() -> None:
    seen: set[Path] = set()
    for candidate in dotenv_candidates():
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        load_dotenv_file(resolved)


def env_float(name: str, fallback: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return fallback
    try:
        return float(raw)
    except ValueError:
        return fallback


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
        self.active_demo_context: Dict[str, Any] = {
            "requestId": "power_buck",
            "domain": "power_electronics",
            "productType": "dc_dc_buck_converter",
            "demoMode": "power_backend",
            "workflowSteps": [],
        }
        self.active_demo_stage_status: Dict[str, str] = {}
        self.agent = self._new_agent()
        self.project_store = ProjectRepository(project_db_path(runtime_base_dir()))
        self.active_project_id: Optional[str] = None
        load_autoee_env()
        self.copilot_timeout_seconds = env_float("AUTOEE_LLM_TIMEOUT_SECONDS", 30.0)
        self.copilot_model_manager = self._new_copilot_model_manager()

    @staticmethod
    def _new_agent() -> AutoEEAgent:
        settings = ModelBackendSettings(default_provider="mock")
        manager = ModelManager(settings=settings, secret_store=MemorySecretStore())
        return AutoEEAgent(state=DesignState(), model_manager=manager)

    @staticmethod
    def _new_copilot_model_manager() -> ModelManager:
        provider_name = (os.getenv("AUTOEE_LLM_PROVIDER", "mock").strip() or "mock").lower()
        settings = ModelBackendSettings(default_provider=provider_name)
        try:
            config = settings.provider_config(provider_name)
        except ValueError:
            provider_name = "mock"
            settings.default_provider = provider_name
            config = settings.provider_config(provider_name)
        model = os.getenv("AUTOEE_LLM_MODEL", "").strip()
        base_url = os.getenv("AUTOEE_LLM_BASE_URL", "").strip()
        api_key_env = os.getenv("AUTOEE_LLM_API_KEY_ENV", "").strip()
        settings.set_provider_config(
            ProviderConfig(
                provider=config.provider,
                model=model or config.model,
                base_url=base_url or config.base_url,
                api_key_env=api_key_env or config.api_key_env,
                secret_name=config.secret_name,
                extra=dict(config.extra),
            )
        )
        return ModelManager(settings=settings)

    def _bump(self) -> None:
        self.version += 1

    def state_payload(self) -> Dict[str, Any]:
        with self.lock:
            payload = build_web_state(
                self.agent.state,
                presentation_status=dict(self.presentation_status),
                running=self.running,
                started_at=self.started_at,
            )
            context = dict(self.active_demo_context)
            demo_stages = []
            for item in context.get("workflowSteps") or []:
                if not isinstance(item, dict):
                    continue
                stage_id = str(item.get("id") or "")
                if not stage_id:
                    continue
                demo_stages.append({
                    "id": stage_id,
                    "title": str(item.get("title") or stage_id),
                    "phase": str(item.get("phase") or ""),
                    "status": self.active_demo_stage_status.get(stage_id, "waiting"),
                })
            payload.update({
                "activeDemoRequestId": context.get("requestId", "power_buck"),
                "activeDemoDomain": context.get("domain", "power_electronics"),
                "activeDemoProductType": context.get("productType", "dc_dc_buck_converter"),
                "demoMode": context.get("demoMode", "power_backend"),
                "activeDemoStages": demo_stages,
                "activeProjectId": self.active_project_id,
            })
            return payload

    @staticmethod
    def _stage_progress(status: str) -> float:
        return {
            "locked": 0.0,
            "waiting": 0.0,
            "pending": 0.0,
            "ready": 15.0,
            "running": 50.0,
            "needs_review": 75.0,
            "partial": 75.0,
            "complete": 100.0,
            "completed": 100.0,
            "verified": 100.0,
            "approved": 100.0,
            "failed": 25.0,
            "error": 25.0,
            "outdated": 60.0,
        }.get(str(status or "").lower(), 0.0)

    def _progress_from_state(self) -> float:
        payload = self.state_payload()
        stages = payload.get("activeDemoStages") or payload.get("stages") or []
        if not stages:
            return 0.0
        score = sum(self._stage_progress(str(item.get("status") or "pending")) for item in stages if isinstance(item, dict))
        return round(score / max(len(stages), 1), 1)

    @staticmethod
    def _infer_title(project_request: str, fallback: str = "AutoEE Project") -> str:
        text = " ".join(str(project_request or "").strip().split())
        if not text:
            return fallback
        for prefix in ["Design a ", "Design an ", "Create a ", "Build a "]:
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix):]
                break
        text = text.rstrip(".")
        return text[:64] or fallback

    @staticmethod
    def _module_status_from_steps(steps: Any, default_status: str = "pending") -> Dict[str, str]:
        result: Dict[str, str] = {}
        if isinstance(steps, list):
            for item in steps:
                if isinstance(item, dict) and item.get("id"):
                    result[str(item["id"])] = str(item.get("status") or default_status)
        return result

    def _project_payload_from_context(self, payload: Dict[str, Any], source_type: str) -> Dict[str, Any]:
        request_text = str(payload.get("projectRequest") or payload.get("requestText") or "")
        domain = str(payload.get("domainId") or payload.get("domain") or "general_pcb")
        product_type = str(payload.get("productType") or "general_hardware_pcb")
        source_demo_id = payload.get("sourceDemoId") or payload.get("requestId")
        title = str(payload.get("title") or self._infer_title(request_text))
        requirement_plan = payload.get("requirementPlan") if isinstance(payload.get("requirementPlan"), dict) else {}
        workflow_steps = payload.get("workflowSteps") if isinstance(payload.get("workflowSteps"), list) else []
        return {
            "title": title,
            "source_type": source_type,
            "source_demo_id": str(source_demo_id) if source_demo_id else None,
            "project_request": request_text,
            "domain_id": domain,
            "product_type": product_type,
            "state": {},
            "requirement_plan": requirement_plan,
            "module_status": self._module_status_from_steps(workflow_steps),
            "progress_percent": 0,
        }

    def list_projects(self) -> List[Dict[str, Any]]:
        return self.project_store.list_projects()

    def get_project(self, project_id: str) -> Dict[str, Any]:
        return self.project_store.get_project(project_id)

    def create_project(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        project_data = self._project_payload_from_context(payload, "diy")
        if not project_data["project_request"]:
            raise ValueError("projectRequest is required.")
        return self.project_store.create_project(**project_data)

    def import_demo_project(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        project_data = self._project_payload_from_context(payload, "demo")
        if not project_data["project_request"]:
            raise ValueError("projectRequest is required.")
        return self.project_store.create_project(**project_data)

    def update_project(self, project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.project_store.update_project(project_id, payload)

    def delete_project(self, project_id: str) -> None:
        with self.lock:
            if self.active_project_id == project_id:
                self.active_project_id = None
        self.project_store.delete_project(project_id)

    def open_project(self, project_id: str) -> Dict[str, Any]:
        project = self.project_store.mark_opened(project_id)
        with self.lock:
            self.active_project_id = project_id
            self.active_demo_context = self._normalize_demo_context({
                "requestId": project.get("sourceDemoId") or project.get("id"),
                "requestText": project.get("projectRequest"),
                "domain": project.get("domainId"),
                "productType": project.get("productType"),
                "workflowSteps": [
                    {"id": key, "title": key, "phase": ""}
                    for key in (project.get("moduleStatus") or {}).keys()
                ],
            })
            self.active_demo_stage_status = {
                key: str(value)
                for key, value in (project.get("moduleStatus") or {}).items()
            }
            self._bump()
        return {"project": project, "state": self.state_payload()}

    def save_active_project_snapshot(self) -> Optional[Dict[str, Any]]:
        if not self.active_project_id:
            return None
        payload = self.state_payload()
        project = self.project_store.get_project(self.active_project_id)
        module_status: Dict[str, str] = {}
        for item in payload.get("activeDemoStages") or payload.get("stages") or []:
            if isinstance(item, dict) and item.get("id"):
                module_status[str(item["id"])] = str(item.get("status") or "pending")
        return self.project_store.update_project(self.active_project_id, {
            "state": payload,
            "moduleStatus": module_status or project.get("moduleStatus") or {},
            "progressPercent": self._progress_from_state(),
        })

    @staticmethod
    def _proposal_from_message(message: str, reply: str) -> Optional[Dict[str, Any]]:
        text = str(message or "").strip()
        lower = text.lower()
        if not any(token in lower for token in ["revise", "change", "modify", "update", "reduce", "improve", "修改", "调整", "优化", "降低"]):
            return None
        target = "requirement_plan"
        if any(token in lower for token in ["bom", "component", "part", "元器件", "物料"]):
            target = "bom"
        elif any(token in lower for token in ["pcb", "layout", "板", "布局"]):
            target = "pcb"
        elif any(token in lower for token in ["simulation", "analysis", "仿真", "分析"]):
            target = "analysis_simulation"
        summary = text[:180]
        return {
            "target_area": target,
            "summary": summary,
            "patch": {
                "kind": "copilot_suggested_revision",
                "request": text,
                "assistantReply": reply,
            },
        }

    def project_copilot_chat(self, project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        project = self.project_store.get_project(project_id)
        messages = payload.get("messages", [])
        message = self.copilot_chat(messages, request_text=str(project.get("projectRequest") or ""))
        task_payload = payload.get("task") if isinstance(payload.get("task"), dict) else {}
        task = self.project_store.upsert_task(
            project_id,
            task_id=task_payload.get("id"),
            title=str(task_payload.get("title") or "Project Task"),
            messages=messages + [{"role": "assistant", "content": message["body"], "from": "assistant", "body": message["body"]}],
            source=str(task_payload.get("source") or "project"),
            status="active",
        )
        latest_user = ""
        for item in reversed(messages if isinstance(messages, list) else []):
            if isinstance(item, dict) and str(item.get("role") or item.get("from")) == "user":
                latest_user = str(item.get("content") or item.get("body") or "")
                break
        proposal_data = self._proposal_from_message(latest_user, str(message.get("body") or ""))
        proposal = None
        if proposal_data:
            proposal = self.project_store.create_proposal(
                project_id,
                source_task_id=task["id"],
                target_area=proposal_data["target_area"],
                summary=proposal_data["summary"],
                patch=proposal_data["patch"],
            )
        return {"message": message, "task": task, "proposal": proposal, "project": self.project_store.get_project(project_id)}

    def apply_project_proposal(self, project_id: str, proposal_id: str) -> Dict[str, Any]:
        project = self.project_store.get_project(project_id)
        proposal = next((item for item in project.get("proposals", []) if item["id"] == proposal_id), None)
        if not proposal:
            raise KeyError(proposal_id)
        requirement_plan = dict(project.get("requirementPlan") or {})
        history = list(requirement_plan.get("revisionHistory") or [])
        history.append({
            "summary": proposal["summary"],
            "targetArea": proposal["targetArea"],
            "appliedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
        requirement_plan["revisionHistory"] = history
        requirement_plan["status"] = "needs_review"
        module_status = {
            key: ("outdated" if value in {"ready", "completed", "verified", "approved"} else value)
            for key, value in (project.get("moduleStatus") or {}).items()
        }
        self.project_store.set_proposal_status(project_id, proposal_id, "applied")
        updated = self.project_store.update_project(project_id, {
            "requirementPlan": requirement_plan,
            "moduleStatus": module_status,
            "progressPercent": 60 if project.get("progressPercent", 0) > 60 else project.get("progressPercent", 0),
        })
        return updated

    def reject_project_proposal(self, project_id: str, proposal_id: str) -> Dict[str, Any]:
        self.project_store.set_proposal_status(project_id, proposal_id, "rejected")
        return self.project_store.get_project(project_id)

    @staticmethod
    def _normalize_copilot_messages(messages: Any) -> List[Dict[str, str]]:
        if not isinstance(messages, list):
            raise ValueError("Expected messages to be a list.")
        normalized: List[Dict[str, str]] = []
        for item in messages[-16:]:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "").strip()
            if not role:
                role = "assistant" if str(item.get("from") or "") == "assistant" else "user"
            if role not in {"user", "assistant"}:
                continue
            content = str(item.get("content") or item.get("body") or "").strip()
            if content:
                normalized.append({"role": role, "content": content})
        if not normalized or normalized[-1]["role"] != "user":
            raise ValueError("The latest copilot message must be from the user.")
        return normalized

    def _copilot_context(self, request_text: str = "") -> Dict[str, Any]:
        payload = self.state_payload()
        return {
            "project_id": self.active_project_id,
            "project_request": request_text or payload.get("prompt"),
            "workflow_status": payload.get("workflowStatus"),
            "running": payload.get("running"),
            "demo_mode": payload.get("demoMode"),
            "domain": payload.get("activeDemoDomain"),
            "product_type": payload.get("activeDemoProductType"),
            "spec": payload.get("spec"),
            "validation_metrics": payload.get("validationMetrics"),
            "evidence_badges": payload.get("evidenceBadges"),
            "recent_logs": (payload.get("logs") or [])[-8:],
        }

    @staticmethod
    def _format_copilot_context(context: Dict[str, Any]) -> str:
        compact = {
            "project_id": context.get("project_id"),
            "project_request": context.get("project_request"),
            "workflow_status": context.get("workflow_status"),
            "running": context.get("running"),
            "demo_mode": context.get("demo_mode"),
            "domain": context.get("domain"),
            "product_type": context.get("product_type"),
            "spec": context.get("spec"),
            "validation_metrics": context.get("validation_metrics"),
            "evidence_badges": context.get("evidence_badges"),
        }
        return json.dumps(compact, sort_keys=True, ensure_ascii=False)

    def copilot_chat(self, messages: Any, request_text: str = "") -> Dict[str, Any]:
        normalized_messages = self._normalize_copilot_messages(messages)
        context_text = self._format_copilot_context(self._copilot_context(request_text))
        system_message = {
            "role": "system",
            "content": (
                "You are AutoEE Copilot inside an engineering IDE/EDA console. "
                "Respond like a Codex-style engineering assistant in an IDE sidebar.\n\n"
                "Conversation style:\n"
                "- Match the user's language.\n"
                "- Answer the user's latest message directly. Treat project context as background, not as the topic.\n"
                "- Keep replies concise, calm, practical, and engineering-focused.\n"
                "- Prefer short paragraphs and flat bullet lists. Use headings only when they help.\n"
                "- Do not use markdown tables unless the user explicitly asks for a table.\n"
                "- Do not dump all workflow status, evidence badges, or context fields by default.\n"
                "- Do not say hello unless the user is greeting you.\n"
                "- Do not use emojis, sales language, or overconfident claims.\n"
                "- Use code fences only for code, commands, configs, or logs.\n\n"
                "AutoEE skills and boundaries:\n"
                "- Help inspect and revise requirement plans, architecture, BOM choices, risks, verification steps, and workflow next actions.\n"
                "- When the user asks for a design change, propose the precise section/module to revise and the expected downstream impact.\n"
                "- Be explicit when data is demo, synthetic, estimated, placeholder, or not signoff.\n"
                "- Do not invent datasheet, safety, certification, supplier, or signoff facts.\n\n"
                f"AutoEE project context:\n{context_text}"
            ),
        }
        response = self.copilot_model_manager.chat(
            [system_message] + normalized_messages,
            timeout=self.copilot_timeout_seconds,
        )
        return {
            "from": "assistant",
            "body": response.text or "AI backend returned an empty response.",
            "provider": response.provider,
            "model": response.model,
            "unavailable": response.unavailable,
            "usage": response.usage,
        }

    def reset(self) -> Dict[str, Any]:
        with self.lock:
            spec = self.agent.state.spec
            self.agent = self._new_agent()
            self.agent.state = DesignState(spec=spec)
            self.presentation_status.clear()
            self.active_demo_stage_status.clear()
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
            self.active_demo_stage_status.clear()
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

    def run_skill_api(self, skill_id: str, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self.lock:
            if self.running:
                raise RuntimeError("Cannot run a skill while the demo workflow is running.")
            self.running = True
            tab_id = "analysis" if skill_id == "power.buck_analysis" else "simulation" if skill_id == "power.buck_simulation" else skill_id
            self.presentation_status[tab_id] = "running"
            self.agent.state.record_event(tab_id, "running", f"Running {skill_id}.")
            self._bump()
        try:
            result = run_local_skill(
                skill_id=skill_id,
                input_data=input_data,
                state=self.agent.state,
                output_root=self.output_root,
            )
            return result.to_dict()
        finally:
            with self.lock:
                self.running = False
                self.presentation_status.clear()
                self._bump()
            self.save_active_project_snapshot()

    def artifact_path(self, run_id: str, module_name: str, artifact_path: str) -> Path:
        base = (self.output_root / run_id / module_name).resolve()
        target = (base / artifact_path).resolve()
        if base not in [target, *target.parents]:
            raise ValueError("Invalid artifact path.")
        if not target.exists() or not target.is_file():
            raise FileNotFoundError(artifact_path)
        return target

    @staticmethod
    def _is_power_demo(context: Dict[str, Any]) -> bool:
        return context.get("requestId") == "power_buck" or context.get("domain") == "power_electronics"

    @staticmethod
    def _normalize_demo_context(context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        raw = context if isinstance(context, dict) else {}
        request_id = str(raw.get("requestId") or "power_buck")
        domain = str(raw.get("domain") or "power_electronics")
        product_type = str(raw.get("productType") or "dc_dc_buck_converter")
        request_text = str(raw.get("requestText") or "")
        workflow_steps = raw.get("workflowSteps") if isinstance(raw.get("workflowSteps"), list) else []
        normalized_steps = []
        for item in workflow_steps:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            normalized_steps.append({
                "id": str(item.get("id")),
                "title": str(item.get("title") or item.get("id")),
                "phase": str(item.get("phase") or ""),
            })
        demo_mode = "power_backend" if request_id == "power_buck" or domain == "power_electronics" else "profile_fake"
        return {
            "requestId": request_id,
            "requestText": request_text,
            "domain": domain,
            "productType": product_type,
            "demoMode": demo_mode,
            "workflowSteps": normalized_steps,
        }

    def run_demo(self, context: Optional[Dict[str, Any]] = None) -> bool:
        demo_context = self._normalize_demo_context(context)
        with self.lock:
            if self.running:
                return False
            spec = self.agent.state.spec
            self.agent = self._new_agent()
            self.agent.state = DesignState(spec=spec)
            self.running = True
            self.stop_requested = False
            self.started_at = time.monotonic()
            self.presentation_status.clear()
            self.active_demo_context = demo_context
            self.active_demo_stage_status = {
                str(item["id"]): "waiting"
                for item in demo_context.get("workflowSteps", [])
                if item.get("id")
            }
            self.agent.stop_requested = False
            self.agent.state.workflow_status = "running"
            self.agent.state.record_event("ui", "reset", "Run Demo reset previous results before starting.")
            self.agent.state.record_event("agent", "running", f"{demo_context['requestId']} demo started.")
            self._bump()
        target = self._run_demo_thread if self._is_power_demo(demo_context) else self._run_profile_demo_thread
        worker = threading.Thread(target=target, name="AutoEEWebDemoRunner", daemon=True)
        worker.start()
        return True

    def _run_profile_demo_thread(self) -> None:
        try:
            with self.lock:
                steps = list(self.active_demo_context.get("workflowSteps") or [])
            for step in steps:
                stage_id = str(step.get("id") or "")
                if not stage_id:
                    continue
                with self.lock:
                    if self.stop_requested:
                        break
                    self.active_demo_stage_status[stage_id] = "running"
                    self.agent.state.record_event(stage_id, "running", f"{step.get('title', stage_id)} demo module is running.")
                    self._bump()

                start = time.monotonic()
                while time.monotonic() - start < self.min_module_seconds:
                    with self.lock:
                        if self.stop_requested:
                            break
                    time.sleep(0.05)

                with self.lock:
                    if self.stop_requested:
                        break
                    self.active_demo_stage_status[stage_id] = "complete"
                    self.agent.state.record_event(stage_id, "complete", f"{step.get('title', stage_id)} fake module completed.")
                    self._bump()

            with self.lock:
                if self.stop_requested:
                    self.agent.state.workflow_status = "stopped"
                    self.agent.state.record_event("agent", "stopped", "Profile demo stopped by user.")
                else:
                    self.agent.state.workflow_status = "complete"
                    self.agent.state.record_event("agent", "complete", f"{self.active_demo_context.get('requestId')} profile demo completed.")
        finally:
            with self.lock:
                self.running = False
                self._bump()
            self.save_active_project_snapshot()

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
                    self.agent.state.record_event("agent", "stopped", "Web Home Page demo stopped by user.")
                elif self.agent.state.workflow_status != "error":
                    self.agent.state.workflow_status = "complete"
                    self.agent.state.record_event("agent", "complete", "Web Home Page demo completed.")
        finally:
            with self.lock:
                self.running = False
                self.presentation_status.clear()
                self._bump()
            self.save_active_project_snapshot()

def create_app(session: Optional[WebDemoSession] = None) -> FastAPI:
    app = FastAPI(title="AutoEE Hardware Agent", docs_url=None, redoc_url=None)
    app.state.session = session or WebDemoSession()

    @app.get("/api/state")
    def get_state() -> JSONResponse:
        return JSONResponse(app.state.session.state_payload())

    @app.get("/api/projects")
    def list_projects() -> JSONResponse:
        return JSONResponse({"ok": True, "projects": app.state.session.list_projects()})

    @app.post("/api/projects")
    def create_project(payload: Dict[str, Any]) -> JSONResponse:
        try:
            project = app.state.session.create_project(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return JSONResponse({"ok": True, "project": project})

    @app.post("/api/projects/import-demo")
    def import_demo_project(payload: Dict[str, Any]) -> JSONResponse:
        try:
            project = app.state.session.import_demo_project(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return JSONResponse({"ok": True, "project": project})

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: str) -> JSONResponse:
        try:
            return JSONResponse({"ok": True, "project": app.state.session.get_project(project_id)})
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Project not found.") from exc

    @app.patch("/api/projects/{project_id}")
    def update_project(project_id: str, payload: Dict[str, Any]) -> JSONResponse:
        try:
            return JSONResponse({"ok": True, "project": app.state.session.update_project(project_id, payload)})
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Project not found.") from exc

    @app.delete("/api/projects/{project_id}")
    def delete_project(project_id: str) -> JSONResponse:
        try:
            app.state.session.delete_project(project_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Project not found.") from exc
        return JSONResponse({"ok": True})

    @app.post("/api/projects/{project_id}/open")
    def open_project(project_id: str) -> JSONResponse:
        try:
            return JSONResponse({"ok": True, **app.state.session.open_project(project_id)})
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Project not found.") from exc

    @app.post("/api/projects/{project_id}/copilot-chat")
    def project_copilot_chat(project_id: str, payload: Dict[str, Any]) -> JSONResponse:
        try:
            return JSONResponse({"ok": True, **app.state.session.project_copilot_chat(project_id, payload)})
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Project not found.") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"LLM backend request failed: {exc}") from exc

    @app.post("/api/projects/{project_id}/proposals/{proposal_id}/apply")
    def apply_project_proposal(project_id: str, proposal_id: str) -> JSONResponse:
        try:
            project = app.state.session.apply_project_proposal(project_id, proposal_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Project or proposal not found.") from exc
        return JSONResponse({"ok": True, "project": project})

    @app.post("/api/projects/{project_id}/proposals/{proposal_id}/reject")
    def reject_project_proposal(project_id: str, proposal_id: str) -> JSONResponse:
        try:
            project = app.state.session.reject_project_proposal(project_id, proposal_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Project or proposal not found.") from exc
        return JSONResponse({"ok": True, "project": project})

    @app.post("/api/run-demo")
    def run_demo(payload: Optional[Dict[str, Any]] = None) -> JSONResponse:
        started = app.state.session.run_demo(payload)
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

    @app.post("/api/run-skill")
    def run_skill(payload: Dict[str, Any]) -> JSONResponse:
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Expected JSON object.")
        skill_id = str(payload.get("skillId") or "")
        input_data = payload.get("input")
        if not skill_id:
            raise HTTPException(status_code=400, detail="skillId is required.")
        if input_data is not None and not isinstance(input_data, dict):
            raise HTTPException(status_code=400, detail="input must be an object.")
        try:
            result = app.state.session.run_skill_api(skill_id, input_data)
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return JSONResponse({"ok": result.get("status") == "completed", "result": result, "state": app.state.session.state_payload()})

    @app.get("/api/artifact/{run_id}/{module_name}/{artifact_path:path}")
    def get_artifact(run_id: str, module_name: str, artifact_path: str) -> FileResponse:
        try:
            target = app.state.session.artifact_path(run_id, module_name, artifact_path)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Artifact not found.") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return FileResponse(target)

    @app.post("/api/copilot-chat")
    def copilot_chat(payload: Dict[str, Any]) -> JSONResponse:
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Expected JSON object.")
        try:
            message = app.state.session.copilot_chat(
                payload.get("messages", []),
                request_text=str(payload.get("requestText") or ""),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"LLM backend request failed: {exc}") from exc
        return JSONResponse({"ok": True, "message": message})

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
