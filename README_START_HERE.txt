AutoEE Hardware Agent - Investor Demo

Project maintenance rule
- After every implementation or UI/content change, update README.md and any relevant start-here/module docs.
- The README update should reflect the current project architecture, module responsibilities, demo capabilities, fake/not-connected boundaries, and run instructions.
- Treat documentation as part of the change, not a separate optional cleanup.
- The same project convention is recorded in skills\project_maintenance.md.

How to start
1. Double-click AutoEE.exe.
2. Click Run 3-Min Demo.
3. Use Investor Demo for the main story, then open Engineering Console for waveforms, loss/thermal, design rationale, and risk details.
4. Click Export Snapshot to create a Markdown summary under the results folder.

Live frontend development
1. Open PowerShell in this repository.
2. Run: powershell -ExecutionPolicy Bypass -File scripts\start_web_dev.ps1
3. Open http://127.0.0.1:5173 in your browser.
4. Edit files under web\src. The browser updates automatically while the dev server is running.

What this build does
- Runs offline with no API key required.
- Presents AutoEE as a modular EE design platform, with Power Electronics as the first executable domain pack.
- Classifies the project request with deterministic keyword rules and selects domain packs, workflow steps, metrics, modules, and artifacts.
- Uses one consistent System Map layout across demos: Design in one row and Test in one row, with steps changing by selected domain.
- Keeps each demo module visible for 0.5 seconds so the run feels fast while still showing progress.
- Includes planning-preview domain packs for RF / Communication, Analog / Sensor, Embedded / MCU, High-Speed Digital, and General PCB.
- Demonstrates a vehicle/industrial 9-36V to 5V/3A USB-C buck charger workflow as the current runnable backend demo.
- Generates a reviewable EE package: specs, first BOM, loss/thermal estimates, synthetic waveforms, control seed, PCB automation plan, fake post-prototype test workflow, validation gaps, and report artifacts.

Evidence policy
- Mock catalog, synthetic waveform, placeholder PCB/3D, and not-signoff labels are intentional.
- Non-power domain packs are placeholder/config-driven planning previews and do not run real engineering solvers yet.
- This demo shows product logic and workflow automation. It is not a hardware signoff package.
- Future adapters can connect real DigiKey, PLECS/LTspice, Maxwell, KiCad, FreeCAD, manufacturing, firmware, and lab data behind the same interfaces.

If the embedded desktop window cannot start, AutoEE opens the same local app in your default browser.
