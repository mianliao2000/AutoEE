from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoee_demo.core.state import DesignState
from evals.metrics import evaluate_design_state, write_evaluation_reports


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate an AutoEE design_state.json file.")
    parser.add_argument("--state", required=True, help="Path to design_state.json.")
    parser.add_argument("--out", default="reports", help="Output directory for eval_summary.json and eval_summary.md.")
    return parser


def main(argv=None) -> int:
    args = build_arg_parser().parse_args(argv)
    state_path = Path(args.state)
    out_dir = Path(args.out)
    state = DesignState.load_json(state_path)
    summary = evaluate_design_state(state)
    paths = write_evaluation_reports(summary, out_dir)
    print(f"Evaluation overall_status={summary.overall_status}")
    for path in paths.values():
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
