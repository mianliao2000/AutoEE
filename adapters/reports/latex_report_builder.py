from __future__ import annotations

from pathlib import Path
from typing import Iterable


def write_equation_bundle(path: Path, equations: Iterable[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "% AutoEE equation bundle.",
        "% This file is ready to be included in a future LaTeX/PDF report.",
        "",
    ]
    for equation in equations:
        label = equation.get("label", "Equation")
        latex = equation.get("latex", "")
        lines.extend([f"% {label}", "\\[", latex, "\\]", ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path

