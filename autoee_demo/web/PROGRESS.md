# AutoEE Web Runtime Progress

## Final Goal
- Provide the polished shareable AutoEE demo surface: a Linear/Codex-style investor UI, local API backend, and Windows portable release folder.
- Keep engineering calculations in Python modules; the web frontend only renders backend-provided state.

## Current Implementation
- Added FastAPI runtime in `autoee_demo/web_app.py` with state, run-demo, stop, reset, export-snapshot, and Server-Sent Events endpoints.
- Added `autoee_demo/web_launcher.py` as the PyInstaller/web desktop entrypoint.
- Added `autoee_demo/web_state.py` to derive investor narrative, metrics, evidence badges, waveforms, loss/thermal data, design rationale, risk summary, and snapshot Markdown from `DesignState`.
- Added Vite + React + TypeScript frontend under `web/`.
- Home Page is now a cinematic product launch page with one visual narrative: requirement -> AutoEE -> reviewable hardware package. It uses the hero copy "Specs -> Hardware" and "AI-Powered Autonomous Hardware Design", a full-bleed dark hardware hero, the PCB image as the main background visual, a `Show Concept` CTA that toggles the large `Example Engineering Console.png` product screenshot on the right, capped responsive first-third hero typography with a small left inset and comfortable image gap so the screenshot occupies most remaining width, and a minimal "Power first. General hardware next." platform expansion band with a muted one-line Power -> Communication -> Sensing -> Embedded -> High-Speed -> Mechanical path instead of dashboard card grids.
- Engineering Console now owns the detailed modular domain-pack workflow planning UI as a neutral engineering cockpit: compact project header, project navigation, selected workflow, engineering modules, validation metrics, artifacts inspector, evidence, waveform overview, loss/thermal, design rationale, risk summary, collapsible logs, and compact developer JSON.
- Engineering Console now supports collapsible side panels: a compact left navigation rail and a right Agent rail with running/done indicators, with open/collapsed state persisted through localStorage.
- Engineering Console sidebar notices and log messages now wrap long exported snapshot paths instead of overflowing into the center workspace.
- Engineering Console now has a persisted Day/Night segmented theme switch scoped to the technical workspace.
- Preset project requests now render distinct fake circuit profiles: buck charger, BLE sensor node, thermocouple front-end, FPGA high-speed board, and general controller board. Placeholder domains show request-specific metrics, module outputs, circuit blocks, and artifacts while clearly remaining not-connected planning previews.
- Run Demo now carries the selected request context. Power runs the existing backend skill chain; non-power requests run isolated fake profile demos, advance only their own workflow steps, and avoid populating buck-specific deterministic results.
- Home Page Run Demo is now an entry action: it switches to Engineering Console, selects the Power Electronics request, and starts the executable power demo instead of sending a browser click event as the run payload.
- Engineering Console detail tabs are domain-specific: power keeps Waveforms and Loss/Thermal, while RF, analog, high-speed, and general PCB requests show appropriate fake planning/review panels instead.
- Standardized all domain-pack roadmaps to the same two-section layout: Design before PCB prototype fabrication and Test after the prototype returns.
- Added packaging assets: `packaging/autoee_web.spec`, `scripts/build_web_release.ps1`, and `README_START_HERE.txt`.
- Generated portable release folder at `release/AutoEE-Investor-Demo/AutoEE.exe`.

## Verification
- `npm --prefix web run build` passes.
- `python -m unittest discover -s tests` passes with 28 tests.
- `python -m autoee_demo.web_launcher --smoke` passes.
- `python -m compileall autoee_demo evals tests tools` passes.
- Web smoke tests initialize the full 11-stage power electronics demo, including the fake post-prototype Test workflow.
- Release folder was scanned for accidental API key pattern; no secrets were found.

## Risks And Notes
- This machine only has Python 3.14. `pywebview` currently fails to install on this stack because its Windows dependency chain pulls `pythonnet`, so the 3.14 build uses browser fallback if embedded WebView is unavailable.
- The dependency marker keeps `pywebview` enabled for Python versions below 3.14, where embedded WebView packaging is expected to be viable.
- Offline demo remains mock/synthetic/not-signoff by design.

## Next Steps
- Build the same release from a Python 3.12 environment to restore embedded WebView as the default desktop window.
- Add web Settings for model backend configuration and API key entry.
- Add visual regression screenshots for 1440x900 and 1920x1080 investor-demo layouts.
