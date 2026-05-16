from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Optional


def configure_matplotlib() -> Any:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def save_line_plot(
    *,
    path: Path,
    title: str,
    x: Iterable[float],
    series: list[tuple[str, Iterable[float]]],
    xlabel: str,
    ylabel: str,
    note: Optional[str] = None,
) -> Path:
    plt = configure_matplotlib()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.2, 3.8), dpi=150)
    for label, values in series:
        ax.plot(list(x), list(values), linewidth=1.8, label=label)
    ax.set_title(title, loc="left", fontsize=10, weight="bold")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, color="#d8dde5", linewidth=0.55, alpha=0.75)
    if len(series) > 1:
        ax.legend(frameon=False, fontsize=8)
    if note:
        ax.text(0.01, 0.02, note, transform=ax.transAxes, fontsize=7, color="#687385")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def save_bar_plot(
    *,
    path: Path,
    title: str,
    labels: list[str],
    values: list[float],
    ylabel: str,
    note: Optional[str] = None,
) -> Path:
    plt = configure_matplotlib()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.2, 3.8), dpi=150)
    ax.bar(labels, values, color="#52575f")
    ax.set_title(title, loc="left", fontsize=10, weight="bold")
    ax.set_ylabel(ylabel)
    ax.grid(True, axis="y", color="#d8dde5", linewidth=0.55, alpha=0.75)
    ax.tick_params(axis="x", labelrotation=20)
    if note:
        ax.text(0.01, 0.02, note, transform=ax.transAxes, fontsize=7, color="#687385")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path

