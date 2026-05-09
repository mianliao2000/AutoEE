# AutoEE Web Runtime Progress

## Final Goal
- Provide the polished shareable AutoEE demo surface: a Linear/Codex-style investor UI, local API backend, and Windows portable release folder.
- Keep engineering calculations in Python modules; the web frontend only renders backend-provided state.

## Current Implementation
- Added FastAPI runtime in `autoee_demo/web_app.py` with state, run-demo, stop, reset, export-snapshot, and Server-Sent Events endpoints.
- Added `autoee_demo/web_launcher.py` as the PyInstaller/web desktop entrypoint.
- Added `autoee_demo/web_state.py` to derive investor narrative, metrics, evidence badges, waveforms, loss/thermal data, design rationale, risk summary, and snapshot Markdown from `DesignState`.
- Added Vite + React + TypeScript frontend under `web/` with Investor Demo, Workflow timeline, Energy Story, Waveform overview, Loss/Thermal, Design Rationale, Risk Summary, and compact developer JSON.
- Added packaging assets: `packaging/autoee_web.spec`, `scripts/build_web_release.ps1`, and `README_START_HERE.txt`.
- Generated portable release folder at `release/AutoEE-Investor-Demo/AutoEE.exe`.

## Verification
- `npm --prefix web run build` passes.
- `python -m unittest discover -s tests` passes with 26 tests.
- `python -m autoee_demo.web_launcher --smoke` passes.
- `python -m compileall autoee_demo evals tests tools` passes.
- `release/AutoEE-Investor-Demo/AutoEE.exe --smoke` finds bundled static assets and initializes 7 demo stages.
- Release folder was scanned for accidental API key pattern; no secrets were found.

## Risks And Notes
- This machine only has Python 3.14. `pywebview` currently fails to install on this stack because its Windows dependency chain pulls `pythonnet`, so the 3.14 build uses browser fallback if embedded WebView is unavailable.
- The dependency marker keeps `pywebview` enabled for Python versions below 3.14, where embedded WebView packaging is expected to be viable.
- Offline demo remains mock/synthetic/not-signoff by design.

## Next Steps
- Build the same release from a Python 3.12 environment to restore embedded WebView as the default desktop window.
- Add web Settings for model backend configuration and API key entry.
- Add visual regression screenshots for 1440x900 and 1920x1080 investor-demo layouts.
