from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def json_loads(value: Optional[str], fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def project_db_path(base_dir: Path) -> Path:
    override = os.getenv("AUTOEE_PROJECT_DB", "").strip()
    if override:
        return Path(override).expanduser()
    return base_dir / "data" / "autoee_projects.sqlite3"


class ProjectRepository:
    """Small local SQLite store for single-user AutoEE web projects."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def _session(self) -> sqlite3.Connection:
        conn = self._connect()
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._session() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                  id TEXT PRIMARY KEY,
                  title TEXT NOT NULL,
                  source_type TEXT NOT NULL,
                  source_demo_id TEXT,
                  project_request TEXT NOT NULL,
                  domain_id TEXT NOT NULL,
                  product_type TEXT NOT NULL,
                  status TEXT NOT NULL,
                  progress_percent REAL NOT NULL DEFAULT 0,
                  state_json TEXT NOT NULL DEFAULT '{}',
                  requirement_plan_json TEXT NOT NULL DEFAULT '{}',
                  module_status_json TEXT NOT NULL DEFAULT '{}',
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  last_opened_at TEXT
                );
                CREATE TABLE IF NOT EXISTS copilot_tasks (
                  id TEXT PRIMARY KEY,
                  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                  title TEXT NOT NULL,
                  source TEXT NOT NULL DEFAULT 'project',
                  status TEXT NOT NULL DEFAULT 'active',
                  messages_json TEXT NOT NULL DEFAULT '[]',
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS change_proposals (
                  id TEXT PRIMARY KEY,
                  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                  source_task_id TEXT,
                  target_area TEXT NOT NULL,
                  summary TEXT NOT NULL,
                  patch_json TEXT NOT NULL DEFAULT '{}',
                  status TEXT NOT NULL DEFAULT 'pending',
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  applied_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_projects_updated_at ON projects(updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_tasks_project ON copilot_tasks(project_id, updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_proposals_project ON change_proposals(project_id, created_at DESC);
                """
            )

    @staticmethod
    def _project_from_row(row: sqlite3.Row, include_json: bool = False) -> Dict[str, Any]:
        result = {
            "id": row["id"],
            "title": row["title"],
            "sourceType": row["source_type"],
            "sourceDemoId": row["source_demo_id"],
            "projectRequest": row["project_request"],
            "domainId": row["domain_id"],
            "productType": row["product_type"],
            "status": row["status"],
            "progressPercent": float(row["progress_percent"] or 0),
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "lastOpenedAt": row["last_opened_at"],
        }
        if include_json:
            result.update({
                "state": json_loads(row["state_json"], {}),
                "requirementPlan": json_loads(row["requirement_plan_json"], {}),
                "moduleStatus": json_loads(row["module_status_json"], {}),
            })
        return result

    @staticmethod
    def _task_from_row(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "projectId": row["project_id"],
            "title": row["title"],
            "source": row["source"],
            "status": row["status"],
            "messages": json_loads(row["messages_json"], []),
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    @staticmethod
    def _proposal_from_row(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "projectId": row["project_id"],
            "sourceTaskId": row["source_task_id"],
            "targetArea": row["target_area"],
            "summary": row["summary"],
            "patch": json_loads(row["patch_json"], {}),
            "status": row["status"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "appliedAt": row["applied_at"],
        }

    def list_projects(self) -> List[Dict[str, Any]]:
        with self._session() as conn:
            rows = conn.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
        return [self._project_from_row(row) for row in rows]

    def get_project(self, project_id: str) -> Dict[str, Any]:
        with self._session() as conn:
            row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
            if not row:
                raise KeyError(project_id)
            project = self._project_from_row(row, include_json=True)
            task_rows = conn.execute(
                "SELECT * FROM copilot_tasks WHERE project_id = ? ORDER BY updated_at DESC",
                (project_id,),
            ).fetchall()
            proposal_rows = conn.execute(
                "SELECT * FROM change_proposals WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
        project["copilotTasks"] = [self._task_from_row(item) for item in task_rows]
        project["proposals"] = [self._proposal_from_row(item) for item in proposal_rows]
        return project

    def create_project(
        self,
        *,
        title: str,
        source_type: str,
        source_demo_id: Optional[str],
        project_request: str,
        domain_id: str,
        product_type: str,
        state: Dict[str, Any],
        requirement_plan: Dict[str, Any],
        module_status: Dict[str, Any],
        progress_percent: float = 0,
    ) -> Dict[str, Any]:
        now = utc_now()
        project_id = f"project-{uuid.uuid4().hex[:12]}"
        with self._session() as conn:
            conn.execute(
                """
                INSERT INTO projects (
                  id, title, source_type, source_demo_id, project_request, domain_id, product_type,
                  status, progress_percent, state_json, requirement_plan_json, module_status_json,
                  created_at, updated_at, last_opened_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    title.strip() or "Untitled Project",
                    source_type,
                    source_demo_id,
                    project_request,
                    domain_id,
                    product_type,
                    "active",
                    float(progress_percent),
                    json_dumps(state),
                    json_dumps(requirement_plan),
                    json_dumps(module_status),
                    now,
                    now,
                    None,
                ),
            )
            self._ensure_default_task(conn, project_id, now)
        return self.get_project(project_id)

    def update_project(self, project_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        allowed = {
            "title": "title",
            "projectRequest": "project_request",
            "domainId": "domain_id",
            "productType": "product_type",
            "status": "status",
            "progressPercent": "progress_percent",
            "state": "state_json",
            "requirementPlan": "requirement_plan_json",
            "moduleStatus": "module_status_json",
        }
        assignments: List[str] = []
        values: List[Any] = []
        for key, column in allowed.items():
            if key not in updates:
                continue
            value = updates[key]
            if key in {"state", "requirementPlan", "moduleStatus"}:
                value = json_dumps(value if isinstance(value, dict) else {})
            assignments.append(f"{column} = ?")
            values.append(value)
        if not assignments:
            return self.get_project(project_id)
        assignments.append("updated_at = ?")
        values.append(utc_now())
        values.append(project_id)
        with self._session() as conn:
            cur = conn.execute(f"UPDATE projects SET {', '.join(assignments)} WHERE id = ?", values)
            if cur.rowcount == 0:
                raise KeyError(project_id)
        return self.get_project(project_id)

    def mark_opened(self, project_id: str) -> Dict[str, Any]:
        now = utc_now()
        with self._session() as conn:
            cur = conn.execute(
                "UPDATE projects SET last_opened_at = ?, updated_at = ? WHERE id = ?",
                (now, now, project_id),
            )
            if cur.rowcount == 0:
                raise KeyError(project_id)
        return self.get_project(project_id)

    def delete_project(self, project_id: str) -> None:
        with self._session() as conn:
            cur = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            if cur.rowcount == 0:
                raise KeyError(project_id)

    def upsert_task(
        self,
        project_id: str,
        *,
        task_id: Optional[str],
        title: str,
        messages: List[Dict[str, Any]],
        source: str = "project",
        status: str = "active",
    ) -> Dict[str, Any]:
        now = utc_now()
        task_id = task_id or f"task-{uuid.uuid4().hex[:12]}"
        with self._session() as conn:
            self._assert_project(conn, project_id)
            conn.execute(
                """
                INSERT INTO copilot_tasks (id, project_id, title, source, status, messages_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  title = excluded.title,
                  source = excluded.source,
                  status = excluded.status,
                  messages_json = excluded.messages_json,
                  updated_at = excluded.updated_at
                """,
                (task_id, project_id, title or "Project Task", source, status, json_dumps(messages), now, now),
            )
            conn.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (now, project_id))
            row = conn.execute("SELECT * FROM copilot_tasks WHERE id = ?", (task_id,)).fetchone()
        return self._task_from_row(row)

    def create_proposal(
        self,
        project_id: str,
        *,
        source_task_id: Optional[str],
        target_area: str,
        summary: str,
        patch: Dict[str, Any],
    ) -> Dict[str, Any]:
        now = utc_now()
        proposal_id = f"proposal-{uuid.uuid4().hex[:12]}"
        with self._session() as conn:
            self._assert_project(conn, project_id)
            conn.execute(
                """
                INSERT INTO change_proposals (
                  id, project_id, source_task_id, target_area, summary, patch_json, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (proposal_id, project_id, source_task_id, target_area, summary, json_dumps(patch), now, now),
            )
            conn.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (now, project_id))
            row = conn.execute("SELECT * FROM change_proposals WHERE id = ?", (proposal_id,)).fetchone()
        return self._proposal_from_row(row)

    def set_proposal_status(self, project_id: str, proposal_id: str, status: str) -> Dict[str, Any]:
        now = utc_now()
        applied_at = now if status == "applied" else None
        with self._session() as conn:
            cur = conn.execute(
                """
                UPDATE change_proposals
                SET status = ?, updated_at = ?, applied_at = COALESCE(?, applied_at)
                WHERE id = ? AND project_id = ?
                """,
                (status, now, applied_at, proposal_id, project_id),
            )
            if cur.rowcount == 0:
                raise KeyError(proposal_id)
            conn.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (now, project_id))
            row = conn.execute("SELECT * FROM change_proposals WHERE id = ?", (proposal_id,)).fetchone()
        return self._proposal_from_row(row)

    @staticmethod
    def _assert_project(conn: sqlite3.Connection, project_id: str) -> None:
        row = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not row:
            raise KeyError(project_id)

    @staticmethod
    def _ensure_default_task(conn: sqlite3.Connection, project_id: str, now: str) -> None:
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        conn.execute(
            """
            INSERT INTO copilot_tasks (id, project_id, title, source, status, messages_json, created_at, updated_at)
            VALUES (?, ?, 'Start Project', 'project', 'active', '[]', ?, ?)
            """,
            (task_id, project_id, now, now),
        )
