from __future__ import annotations

import argparse
from pathlib import Path


PROJECT_TEMPLATE = """# AutoEE Project Progress

## Final Goal
- Build an AI-native power electronics workflow app with decoupled skills/modules.

## Current Implementation
- Update this section after each implementation pass.

## Verification Status
- Add test commands and results.

## Risks And Blockers
- Add known blockers.

## Next Steps
- Add the next concrete implementation step.
"""


MODULE_TEMPLATE = """# {title} Progress

## Final Goal
- Describe the module goal.

## Completed
- Describe completed implementation.

## Verification
- Describe tests or manual checks.

## Risks And Blockers
- Describe blockers.

## Next Steps
- Describe the next concrete step.
"""


def ensure_project_progress(root: Path) -> Path:
    path = root / "docs" / "progress" / "PROJECT_PROGRESS.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(PROJECT_TEMPLATE, encoding="utf-8")
    return path


def ensure_module_progress(root: Path, module: str) -> Path:
    path = root / "autoee_demo" / "modules" / module / "PROGRESS.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        title = module.replace("_", " ").title()
        path.write_text(MODULE_TEMPLATE.format(title=title), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or verify AutoEE progress reports.")
    parser.add_argument("--module", help="Module id to create/check.")
    parser.add_argument("--check", action="store_true", help="Fail if the requested progress file is missing.")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    project_path = root / "docs" / "progress" / "PROJECT_PROGRESS.md"
    module_path = root / "autoee_demo" / "modules" / args.module / "PROGRESS.md" if args.module else None

    if args.check:
        missing = []
        if not project_path.exists():
            missing.append(str(project_path))
        if module_path is not None and not module_path.exists():
            missing.append(str(module_path))
        if missing:
            print("Missing progress report(s):")
            for path in missing:
                print(f"- {path}")
            return 1
        print("Progress reports OK.")
        return 0

    print(f"Project progress: {ensure_project_progress(root)}")
    if args.module:
        print(f"Module progress: {ensure_module_progress(root, args.module)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

