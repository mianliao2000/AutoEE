AutoEE Hardware Agent - Home Page

Project maintenance rule
- After every implementation or UI/content change, update README.md and any relevant start-here/module docs.
- The README update should reflect the current project architecture, module responsibilities, demo capabilities, fake/not-connected boundaries, and run instructions.
- Treat documentation as part of the change, not a separate optional cleanup.
- The same project convention is recorded in skills\project_maintenance.md.

How to start
1. Double-click AutoEE.exe.
2. Click Run Demo. From Home Page this opens Engineering Console and starts the Power Electronics demo; from Engineering Console it resets previous demo results first, clears the System Map back to white waiting cards, then starts a fresh run.
3. The app opens in Engineering Console by default for workflow, waveforms, loss/thermal, design rationale, risk details, logs, and developer state. Switch to Home Page for the high-level product story.
4. Click Export Snapshot to create a Markdown summary under the results folder.

Live frontend development
1. Open PowerShell in this repository.
2. Run: powershell -ExecutionPolicy Bypass -File scripts\start_web_dev.ps1
3. Open http://127.0.0.1:5173 in your browser.
4. Edit files under web\src. The browser updates automatically while the dev server is running.

What this build does
- Runs offline with no API key required.
- Presents AutoEE as a modular hardware design platform, with Power Electronics as the first executable domain pack.
- Home Page is a cinematic product launch page: requirement -> AutoEE -> reviewable hardware package.
- Home Page hero copy is "Specs -> Hardware" with the subtitle "AI-Powered Autonomous Hardware Design".
- Home Page uses a full-bleed dark hardware hero, minimal copy, and a large `Example Engineering Console.png` engineering-console product screenshot that toggles after clicking `Show Concept`.
- Home Page keeps short desktop hero/package/platform text on one line where the viewport allows it.
- Home Page keeps hero text sizing stable on desktop and resizes the right-side screenshot first so the image and copy do not overlap on different monitors.
- Home Page hero keeps the AutoEE copy inside the first third of the display with capped responsive type and a small left inset, then gives the revealed concept screenshot most of the remaining width with a comfortable gap.
- Home Page keeps a black/white/neutral product-poster style with very limited accent color.
- Platform Expansion uses the title "Power first. General hardware next." and shows a compact one-line Power -> Communication -> Sensing -> Embedded -> High-Speed -> Mechanical path.
- Engineering Console is the technical cockpit for detailed workflows, module internals, validation metrics, evidence, forms, and collapsible logs.
- Engineering Console uses a compact project header and neutral EDA-style workspace instead of the Home Page marketing hero.
- Engineering Console keeps Project Understanding directly above System Map, with generated package and evidence panels in the right sidebar.
- Engineering Console supports collapsible left/right side panels that expand the center workspace.
- Engineering Console wraps long exported snapshot paths inside the sidebar notice/log panels.
- Engineering Console has a Day/Night segmented theme switch in the project header.
- Classifies the project request with deterministic keyword rules and selects domain packs, workflow steps, metrics, modules, and artifacts.
- Provides a DIY Request option for real free-text input, separate from the preset demo requests.
- Opens with Power Electronics selected as the default runnable demo.
- Uses one consistent System Map layout across demos: Design in one row and Test in one row, with steps changing by selected domain.
- Runs only the currently selected request when you click Run Demo: Power uses the executable buck workflow, while non-power requests use isolated fake profile demos.
- Gives each preset request its own fake circuit profile, metrics, module outputs, circuit blocks, detail tabs, and artifact package instead of showing every request as the 15W USB-C buck charger.
- Hides power-only Waveforms and Loss/Thermal tabs for non-power requests and replaces them with RF, analog, embedded, high-speed, or general PCB review panels.
- Keeps each demo module visible for 0.5 seconds so the run feels fast while still showing progress.
- Includes planning-preview domain packs for RF / Communication, Analog / Sensor, Embedded / MCU, High-Speed Digital, and General PCB.
- Demonstrates a vehicle/industrial 9-36V to 5V/3A USB-C buck charger workflow as the current runnable backend demo.
- Generates a reviewable hardware package: specs, first BOM, loss/thermal estimates, synthetic waveforms, control seed, PCB automation plan, fake post-prototype test workflow, validation gaps, and report artifacts.

Evidence policy
- Mock catalog, synthetic waveform, placeholder PCB/3D, and not-signoff labels are intentional.
- Non-power domain packs are placeholder/config-driven planning previews and do not run real engineering solvers yet.
- This demo shows product logic and workflow automation. It is not a hardware signoff package.
- Future adapters can connect real DigiKey, PLECS/LTspice, Maxwell, KiCad, FreeCAD, manufacturing, firmware, and lab data behind the same interfaces.

If the embedded desktop window cannot start, AutoEE opens the same local app in your default browser.
