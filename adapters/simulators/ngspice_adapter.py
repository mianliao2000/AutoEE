from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class NgspiceRun:
    connected: bool
    backend: str
    log: str
    raw_path: Optional[Path] = None


def adapter_status() -> dict[str, object]:
    executable = shutil.which("ngspice")
    return {
        "adapter": "ngspice",
        "connected": bool(executable),
        "executable": executable or "",
        "message": "ngspice executable found." if executable else "Simulator adapter not connected.",
    }


def run_netlist(netlist_path: Path, output_dir: Path, timeout_s: int = 20) -> NgspiceRun:
    status = adapter_status()
    executable = str(status.get("executable") or "")
    if not executable:
        return NgspiceRun(False, "ngspice", "Simulator adapter not connected.")
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "ngspice.log"
    raw_path = output_dir / "raw_output.raw"
    command = [executable, "-b", "-o", str(log_path), "-r", str(raw_path), str(netlist_path)]
    try:
        subprocess.run(command, cwd=output_dir, check=True, timeout=timeout_s)
    except Exception as exc:
        return NgspiceRun(True, "ngspice", f"ngspice failed: {type(exc).__name__}: {exc}", raw_path if raw_path.exists() else None)
    return NgspiceRun(True, "ngspice", log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else "ngspice completed.", raw_path if raw_path.exists() else None)

