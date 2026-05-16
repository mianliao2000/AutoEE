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
- Home Page centers the disclaimer "Created by Jackson Liao, © 2026 Pandora AI. All rights reserved." above the hero image and stays locked to a single viewport without page scrolling.
- Engineering Console is the technical cockpit for detailed workflows, module internals, validation metrics, evidence, forms, and logs.
- Engineering Console uses an IDE / EDA-style layout: Design/Test workflow and artifacts on the left, Requirement/Analysis/Simulation/BOM/PCB/Review workspace in the center, and AI Design Assistant on the right.
- BOM appears before PCB in the workflow because component decisions should be reviewed before board layout starts.
- Engineering Console now reduces obvious dashboard card separation: the left workflow uses compact tree/list rows, artifacts read as a file tree, editor tabs sit on one continuous workspace, the right assistant reads as a copilot panel, and console output is integrated as a terminal-style log strip.
- Engineering Console Requirement is now a Design Plan / Engineering Brief step with seven reviewable sections, targeted section revision, reviewed state, Copilot transcript updates, and approval gating before downstream modules become ready.
- Requirement uses an Engineering Brief review layout with a compact plan header, reviewed-section progress, readable selectable sections, a right-side review inspector, and section actions shown only for the selected review context.
- Reviewed Requirement sections use a subtle green row state and green badge.
- Requirement no longer shows BOM or other downstream outputs; BOM appears only in the BOM tab.
- Engineering Console BOM is now a Component Decision Workspace with summary counts, filters, engineering columns, selected-part inspector, rationale, alternatives, derating checks, risk/evidence state, approve/lock/replace actions, CSV export, and Copilot review actions.
- BOM workspace labels, filters, status badges, inspector headings, and common demo evidence/risk strings switch between English and Chinese.
- BOM includes ActiveBOM-style workflow ideas: Engineering/Procurement/Risk BOM sets, category/manufacturer/status grouping, BOM checks, lifecycle, stock, cost, evidence, and alternative-solution visibility.
- Engineering Console Copilot uses a VS Code Codex-style multi-task panel with a recent-task list, search, new task action, per-task delete action, expanded panel mode, model/settings menu, task-view toggle, and independent message history per task.
- Copilot no longer shows `CODEX` / `CLAUDE CODE` provider tabs. The composer includes example ChatGPT/Gemini/Claude/DeepSeek/Qwen model choices, intelligence levels, and demo usage remaining controls while the demo backend still routes through the configured provider.
- Engineering Console Copilot chat keeps the Codex-style thread: user messages are right-aligned bubbles and AutoEE responses are normal assistant prose with parsed paragraphs, bullets, inline code, and code blocks.
- `/api/copilot-chat` uses a Codex-style engineering assistant prompt for MiniMax/OpenAI-compatible providers and keeps AutoEE project context in the system prompt so replies answer the latest user request instead of dumping raw context/status tables.
- Engineering Console sidebars collapse to compact rails and the center workspace expands automatically.
- Engineering Console lets the left workflow sidebar and right AutoEE Copilot panel be resized by dragging their edges up to roughly half of the available screen/container. Console Output can be resized vertically up to roughly half the workspace by dragging its top edge and can be hidden or shown from its header.
- Engineering Console validates persisted resizable pane sizes on load so the AutoEE Copilot panel and Console Output cannot reopen at zero size.
- Engineering Console resize handles update pane dimensions directly while dragging, then persist the final size on pointer release.
- Engineering Console now keeps explanatory UI copy minimal by default and prioritizes images, generated results, tables, logs, and controls.
- Engineering Console waveform, Bode, efficiency, loss, pie, and thermal visuals now use theme-aware black/white chart styling so they switch with Day/Night mode.
- Engineering Console includes a compact top toolbar with Run Demo, Reset, bilingual `中 / EN` language toggle, theme toggle, and one merged run progress / review status control with a percentage readout.
- Engineering Console top toolbar includes `My Projects / 我的项目` for the local project dashboard and `Add to My Projects / 添加到我的项目` for copying the current demo/template into a user-owned project.
- My Projects uses hash routes without adding a router dependency: `#/projects` lists local SQLite-backed project cards with progress percentages, and `#/projects/:id` shows the selected project's Design/Test modules, requirement summary, recent state, and pending AI change proposals.
- My Projects now has a Pandora AI-style dashboard top bar, centered project grid, rounded progress cards, bilingual controls, and Day/Night theme switching.
- Local project data is stored in SQLite at `runtime_base_dir()/data/autoee_projects.sqlite3` by default, with `AUTOEE_PROJECT_DB` available for tests or custom storage.
- When a project is open, Copilot tasks become project-scoped and AI design changes are staged as proposals until the user applies or rejects them.
- The Engineering Console top toolbar no longer has a Home Page button; click the left `AE` logo to return to Home Page.
- Downstream modules show their Run action inside the module workspace instead of relying on a global Run Module button.
- Engineering Console Reset applies only to preset demo requests, removes demo/requirement Copilot tasks, and preserves manually created Copilot tasks. The copilot composer sends on Enter and keeps Shift+Enter for a line break.
- Engineering Console fits within the browser viewport without outer page scrolling; the left, center, and right panes each scroll internally when needed.
- Engineering Console uses `New Design` for free-text project input; sending the text mirrors it into the active AI Design Assistant task. Copilot tasks persist in `localStorage` with `autoee.engineering.copilotTasks` and `autoee.engineering.activeCopilotTaskId`. The chat composer calls the local `/api/copilot-chat` backend and uses the LLM provider configured in `.env`.
- Copy `.env.example` to `.env`, set `AUTOEE_LLM_PROVIDER`, `AUTOEE_LLM_MODEL`, optional `AUTOEE_LLM_BASE_URL`, and the matching API key. Supported Copilot providers include `openai`, `anthropic`, `gemini`, `minimax`, `deepseek`, `qwen`, `openrouter`, `ollama`, `custom_openai`, and `mock`. `.env` is ignored by git and `.env.example` includes future OpenRouter model-routing names for ChatGPT, Gemini, Claude, DeepSeek, and Qwen.
- Default/reset BOM views stay blank until the Component Selection/BOM module runs, then show reviewable component decisions instead of a static part list.
- Engineering Console no longer exposes the web snapshot/export-package action or Focus Mode.
- Engineering Console has a compact sun/moon Day/Night icon toggle that changes surfaces, text, dividers, canvas, plot, assistant, console, and status colors. The adjacent `中 / EN` switch persists the UI language in `localStorage` and localizes the main console shell, Requirement controls, Copilot task controls, console header, and Home Page hero/footer.
- Engineering Console uses a VS Code-inspired dark color system instead of blue-heavy navy dashboard surfaces, with neutral editor/sidebar/tab colors, subtle dividers, and semantic status colors only for active/running, completed, needs-review, and failed states.
- Requirement includes a bilingual key-metrics table and switches the demo design brief content between English and Chinese.
- Engineering Console uses a refined typography system: Inter/Geist/system UI sans for interface text, mono fonts only for logs, timestamps, schematic labels, waveform labels, and engineering/numeric data, with calmer 400/500 weights and tabular numbers.
- Classifies the project request with deterministic keyword rules and selects domain packs, workflow steps, metrics, modules, and artifacts.
- Provides a New Design option for real free-text input, separate from the preset demo requests.
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
