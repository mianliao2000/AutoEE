export type ProjectDomain =
  | "power_electronics"
  | "rf_communication"
  | "analog_sensor"
  | "embedded_mcu"
  | "high_speed_digital"
  | "general_pcb";

export type ModuleStatusCategory = "required" | "recommended" | "optional" | "disabled";

export interface ProjectClassification {
  primaryDomain: ProjectDomain;
  domains: ProjectDomain[];
  productType: string;
  confidence: "high" | "medium" | "low";
  reasons: string[];
  source: "deterministic_keyword_rules";
}

export interface WorkflowStep {
  id: string;
  title: string;
  phase: string;
  contextLabel: string;
  description: string;
  icon: string;
  sourceStageIds: string[];
  moduleIds: string[];
}

export interface CapabilityModule {
  id: string;
  name: string;
  description: string;
  statusCategory: ModuleStatusCategory;
  domain: ProjectDomain;
  reason: string;
  inputArtifacts: string[];
  outputArtifacts: string[];
  icon: string;
  appearsInWorkflow: boolean;
}

export interface MetricDefinition {
  id: string;
  label: string;
  description: string;
  domain: ProjectDomain;
  backendMetricKey?: string;
  pendingLabel: string;
}

export interface ArtifactDefinition {
  id: string;
  label: string;
  description: string;
  domain: ProjectDomain;
  sourceStageIds: string[];
  statusLabel: string;
}

export interface DomainPack {
  id: ProjectDomain;
  name: string;
  description: string;
  classifierHints: string[];
  uiLabels: {
    workflowTitle: string;
    workflowSubtitle: string;
    packageTitle: string;
  };
  workflowSteps: WorkflowStep[];
  capabilities: CapabilityModule[];
  metrics: MetricDefinition[];
  artifacts: ArtifactDefinition[];
  placeholder: boolean;
}

export interface ModuleSelectionResult {
  required: CapabilityModule[];
  recommended: CapabilityModule[];
  optional: CapabilityModule[];
  disabled: CapabilityModule[];
}

export interface WorkflowSection {
  label: string;
  contextLabel: string;
  steps: WorkflowStep[];
}

export interface WorkflowPlan {
  requestText: string;
  classification: ProjectClassification;
  selectedPacks: DomainPack[];
  workflowSteps: WorkflowStep[];
  workflowSections: WorkflowSection[];
  modules: ModuleSelectionResult;
  metrics: MetricDefinition[];
  artifacts: ArtifactDefinition[];
  capabilityNotice: string;
}

export interface DemoProjectRequest {
  id: string;
  label: string;
  request: string;
}

const DESIGN_PHASE = "Design";
const TEST_PHASE = "Test";
const BEFORE_PROTOTYPE = "Before PCB Prototype Fabrication";
const AFTER_PROTOTYPE = "After PCB Prototype Returns";

const powerWorkflow: WorkflowStep[] = [
  {
    id: "specifications",
    title: "Specifications",
    phase: "Design",
    contextLabel: "Before PCB Prototype Fabrication",
    description: "Translate the product request into electrical targets, acceptance limits, and a plan for the design run.",
    icon: "file",
    sourceStageIds: ["understand_specs"],
    moduleIds: ["specs_parser"],
  },
  {
    id: "parts",
    title: "Parts",
    phase: "Design",
    contextLabel: "Before PCB Prototype Fabrication",
    description: "Select a first-pass power-stage BOM and supplier-backed candidates for review.",
    icon: "chip",
    sourceStageIds: ["select_parts"],
    moduleIds: ["component_selection", "topology_selection"],
  },
  {
    id: "analysis",
    title: "Analysis",
    phase: "Design",
    contextLabel: "Before PCB Prototype Fabrication",
    description: "Estimate losses, thermal risk, magnetic readiness, and early design constraints.",
    icon: "chart",
    sourceStageIds: ["loss_thermal", "em_readiness"],
    moduleIds: ["loss_analysis", "thermal_estimation", "emi_risk_review"],
  },
  {
    id: "simulation",
    title: "Simulation",
    phase: "Design",
    contextLabel: "Before PCB Prototype Fabrication",
    description: "Generate ripple, transient, switch-node, and inductor-current waveform evidence.",
    icon: "activity",
    sourceStageIds: ["waveforms"],
    moduleIds: ["power_waveform_simulation"],
  },
  {
    id: "control",
    title: "Control",
    phase: "Design",
    contextLabel: "Before PCB Prototype Fabrication",
    description: "Create a first control-loop seed and stability estimate for the converter.",
    icon: "sliders",
    sourceStageIds: ["control"],
    moduleIds: ["loop_stability"],
  },
  {
    id: "pcb",
    title: "PCB",
    phase: "Design",
    contextLabel: "Before PCB Prototype Fabrication",
    description: "Prepare layout rules, PCB automation plan, manufacturing handoff, and review package.",
    icon: "board",
    sourceStageIds: ["package"],
    moduleIds: ["power_layout_rules", "report_generation"],
  },
  {
    id: "embedded_coding_download",
    title: "Codes",
    phase: "Test",
    contextLabel: "After PCB Prototype Returns",
    description: "Build firmware, flash the returned board, and record bring-up logs.",
    icon: "code",
    sourceStageIds: ["embedded_coding_download"],
    moduleIds: ["firmware_bringup"],
  },
  {
    id: "closed_loop_tuning",
    title: "Tuning",
    phase: "Test",
    contextLabel: "After PCB Prototype Returns",
    description: "Run a bench tuning sweep and select control parameters.",
    icon: "sliders",
    sourceStageIds: ["closed_loop_tuning"],
    moduleIds: ["bench_loop_tuning"],
  },
  {
    id: "efficiency_logging",
    title: "Data",
    phase: "Test",
    contextLabel: "After PCB Prototype Returns",
    description: "Record efficiency, ripple, thermal, and instrument data.",
    icon: "database",
    sourceStageIds: ["efficiency_logging"],
    moduleIds: ["bench_data_logging"],
  },
  {
    id: "test_report",
    title: "Report",
    phase: "Test",
    contextLabel: "After PCB Prototype Returns",
    description: "Generate post-prototype evidence, pass/fail checks, and revision actions.",
    icon: "report",
    sourceStageIds: ["test_report"],
    moduleIds: ["post_prototype_report"],
  },
];

const packs: DomainPack[] = [
  {
    id: "power_electronics",
    name: "Power Electronics",
    description: "DC/DC converters, chargers, rails, power stages, loss/thermal checks, control, and power-layout review.",
    classifierHints: ["buck", "boost", "converter", "charger", "dc-dc", "usb-c", "vin", "vout", "5v", "12v", "24v", "36v", "amp", "power supply"],
    uiLabels: {
      workflowTitle: "Selected Workflow",
      workflowSubtitle: "Power electronics pack: design before fabrication, then test after the prototype returns.",
      packageTitle: "Generated EE Package",
    },
    workflowSteps: powerWorkflow,
    capabilities: [
      module("specs_parser", "Specs Parser", "Turns the product request into electrical limits and acceptance criteria.", "required", "power_electronics", "Every design needs a structured requirement baseline.", ["Project request"], ["Constraint matrix"], "file"),
      module("topology_selection", "Topology Selection", "Chooses the starting power topology and operating point.", "required", "power_electronics", "The request maps to a step-down charger, so topology choice is central.", ["Constraint matrix"], ["Topology candidate"], "board"),
      module("component_selection", "Component Selection", "Builds the first power-stage BOM candidate set.", "required", "power_electronics", "MOSFETs, inductor, capacitors, and supply constraints drive the design.", ["Topology candidate"], ["Initial BOM"], "chip"),
      module("loss_analysis", "Loss Analysis", "Estimates conduction, switching, magnetic, capacitor, and PCB losses.", "required", "power_electronics", "Power converters need loss estimates to size parts and thermal margin.", ["Initial BOM"], ["Loss model"], "chart"),
      module("thermal_estimation", "Thermal Estimation", "Turns loss estimates into component temperature risk.", "recommended", "power_electronics", "Thermal risk matters for vehicle and industrial operating conditions.", ["Loss model"], ["Thermal estimate"], "activity"),
      module("loop_stability", "Loop Stability", "Creates a control seed and stability estimate.", "recommended", "power_electronics", "Closed-loop behavior is relevant for regulated converters.", ["Plant estimate", "Waveforms"], ["Control plan"], "sliders"),
      module("power_layout_rules", "Power Layout Rules", "Prepares hot-loop, current path, and copper-area layout constraints.", "required", "power_electronics", "Layout quality strongly affects EMI, temperature, and switching behavior.", ["BOM", "Topology"], ["Layout constraints"], "board"),
      module("emi_risk_review", "EMI Risk Review", "Flags switching-loop and magnetics risks before layout signoff.", "recommended", "power_electronics", "High dv/dt and di/dt require early EMI awareness.", ["Topology", "Layout constraints"], ["EMI checklist"], "activity"),
      module("report_generation", "Report Generation", "Creates a reviewable design package and signoff gaps.", "required", "power_electronics", "The demo must end in a reviewable engineering artifact.", ["All module outputs"], ["Review report"], "report"),
    ],
    metrics: [
      metric("efficiency", "Efficiency", "Estimated converter efficiency.", "power_electronics", "efficiency", "Estimated after loss analysis"),
      metric("loss", "Loss", "Total watts that become heat.", "power_electronics", "totalLoss", "Estimated after loss analysis"),
      metric("hot_spot", "Hot Spot", "Highest estimated component temperature.", "power_electronics", "maxTemp", "Estimated after thermal module"),
      metric("ripple", "Ripple", "Output ripple estimate or waveform-derived result.", "power_electronics", "voutRipple", "Estimated after simulation"),
      metric("transient", "Transient", "Load-step deviation estimate.", "power_electronics", "transient", "Estimated after simulation"),
    ],
    artifacts: [
      artifact("constraint_matrix", "Constraint Matrix", "Voltage, current, ripple, transient, efficiency, and thermal targets.", "power_electronics", ["understand_specs"], "deterministic estimate"),
      artifact("initial_bom", "Initial BOM", "First-pass selected parts with source labels.", "power_electronics", ["select_parts"], "fake distributor data"),
      artifact("loss_thermal", "Loss and Thermal Model", "Loss breakdown and component temperature estimate.", "power_electronics", ["loss_thermal"], "demo estimate"),
      artifact("waveforms", "Ripple / Transient Waveforms", "Synthetic buck converter waveform evidence.", "power_electronics", ["waveforms"], "synthetic not signoff"),
      artifact("layout_rules", "Layout Rules", "Hot-loop, PDN, EMI, and manufacturing constraints.", "power_electronics", ["package"], "placeholder plan"),
      artifact("review_report", "Review Report", "Design package, risks, missing evidence, and next actions.", "power_electronics", ["test_report", "package"], "review draft"),
    ],
    placeholder: false,
  },
  placeholderPack("rf_communication", "RF / Communication", "Wireless links, RF front-end choices, antennas, matching, RF layout, and compliance planning.", ["rf", "wireless", "ble", "bluetooth", "2.4 ghz", "wifi", "antenna", "lora", "zigbee"], [
    step("rf_requirements", "RF Requirements", DESIGN_PHASE, BEFORE_PROTOTYPE, "Identify frequency band, range target, power limit, antenna needs, and compliance region.", "file", ["frequency_plan"]),
    step("rf_ic_selection", "RF IC", DESIGN_PHASE, BEFORE_PROTOTYPE, "Shortlist RF SoCs or transceivers and required matching parts.", "chip", ["rf_ic_selection"]),
    step("link_budget", "Link Budget", DESIGN_PHASE, BEFORE_PROTOTYPE, "Estimate path loss, margin, transmit power, receiver sensitivity, and range risk.", "chart", ["link_budget"]),
    step("antenna_matching", "Antenna / Matching", DESIGN_PHASE, BEFORE_PROTOTYPE, "Select antenna approach and reserve matching-network strategy.", "activity", ["antenna_selection", "matching_network"]),
    step("rf_layout", "RF Layout", DESIGN_PHASE, BEFORE_PROTOTYPE, "Capture keep-outs, feedline, ground, antenna clearance, and RF layout rules.", "board", ["rf_layout_rules"]),
    step("wireless_compliance", "Compliance", TEST_PHASE, AFTER_PROTOTYPE, "List region-specific wireless compliance checks and test readiness.", "report", ["wireless_compliance_review"]),
  ], [
    ["link_margin", "Link Margin"], ["range", "Range Estimate"], ["tx_power", "TX Power"], ["rx_sensitivity", "RX Sensitivity"], ["antenna_risk", "Antenna Risk"],
  ], [
    "Frequency Plan", "RF IC Shortlist", "Link Budget", "Antenna / Matching Notes", "RF Layout Constraints", "Compliance Checklist",
  ]),
  placeholderPack("analog_sensor", "Analog / Sensor", "Low-noise sensor interfaces, signal chains, ADC selection, noise budgets, calibration, and analog layout rules.", ["analog", "sensor", "thermocouple", "front-end", "adc", "op amp", "low-noise", "measurement"], [
    step("signal_chain", "Signal Chain", DESIGN_PHASE, BEFORE_PROTOTYPE, "Define the sensor, gain, filtering, ADC, reference, and calibration chain.", "activity", ["signal_chain_design"]),
    step("sensor_selection", "Sensor", DESIGN_PHASE, BEFORE_PROTOTYPE, "Select sensor class and input protection approach.", "chip", ["sensor_selection"]),
    step("op_amp_adc", "Op Amp / ADC", DESIGN_PHASE, BEFORE_PROTOTYPE, "Shortlist amplifier, ADC, reference, and filter components.", "chip", ["op_amp_selection", "adc_selection"]),
    step("noise_budget", "Noise Budget", DESIGN_PHASE, BEFORE_PROTOTYPE, "Estimate noise contributors, bandwidth, resolution, and accuracy risk.", "chart", ["noise_analysis"]),
    step("analog_layout", "Analog Layout", DESIGN_PHASE, BEFORE_PROTOTYPE, "Capture grounding, guard, shielding, and sensitive-node layout rules.", "board", ["analog_layout_rules"]),
    step("calibration", "Calibration", TEST_PHASE, AFTER_PROTOTYPE, "Plan calibration data, drift checks, and production trim strategy.", "sliders", ["calibration_plan"]),
  ], [
    ["noise", "Noise"], ["bandwidth", "Bandwidth"], ["resolution", "Resolution"], ["accuracy", "Accuracy"], ["drift_risk", "Drift Risk"],
  ], [
    "Signal Chain", "Sensor / ADC Selection", "Noise Budget", "Calibration Plan", "Analog Layout Rules", "Review Report",
  ]),
  placeholderPack("embedded_mcu", "Embedded / MCU", "MCU/SoC selection, pin maps, firmware architecture, power modes, interfaces, debug, and manufacturing test.", ["mcu", "microcontroller", "firmware", "embedded", "coin cell", "battery", "gpio", "programming header", "sensor node"], [
    step("mcu_selection", "MCU / SoC", DESIGN_PHASE, BEFORE_PROTOTYPE, "Select the MCU or SoC class and resource envelope.", "chip", ["mcu_selection"]),
    step("pin_map", "Pin Map", DESIGN_PHASE, BEFORE_PROTOTYPE, "Allocate interfaces, GPIO, debug pins, ADC channels, and constraints.", "board", ["pin_map"]),
    step("firmware_architecture", "Firmware", DESIGN_PHASE, BEFORE_PROTOTYPE, "Plan tasks, drivers, telemetry, boot, update, and failure handling.", "code", ["firmware_architecture"]),
    step("embedded_power_budget", "Power Budget", DESIGN_PHASE, BEFORE_PROTOTYPE, "Estimate active and sleep current budget across modes.", "chart", ["power_budget"]),
    step("interface_selection", "Interfaces", DESIGN_PHASE, BEFORE_PROTOTYPE, "Select buses, connectors, sensors, radios, and programming interfaces.", "activity", ["interface_selection"]),
    step("manufacturing_test", "Test Plan", TEST_PHASE, AFTER_PROTOTYPE, "Plan programming, test pads, bring-up, and manufacturing test coverage.", "report", ["manufacturing_test_plan"]),
  ], [
    ["battery_life", "Battery Life"], ["sleep_current", "Sleep Current"], ["io_usage", "I/O Usage"], ["firmware_risk", "Firmware Risk"], ["bom_cost", "BOM Cost"],
  ], [
    "MCU / SoC Selection", "Pin Map", "Firmware Architecture", "Power Budget", "Interface Map", "Manufacturing Test Plan",
  ]),
  placeholderPack("high_speed_digital", "High-Speed Digital", "Processor or FPGA boards, DDR, USB/PCIe, signal integrity, power integrity, stackup, impedance, and timing constraints.", ["fpga", "ddr", "usb 3", "usb3", "pcie", "ethernet", "serdes", "memory", "impedance", "high-speed"], [
    step("processor_fpga", "Processor / FPGA", DESIGN_PHASE, BEFORE_PROTOTYPE, "Select processor or FPGA class and high-speed interface requirements.", "chip", ["processor_or_fpga_selection"]),
    step("memory_interface", "Memory", DESIGN_PHASE, BEFORE_PROTOTYPE, "Define DDR or memory topology, termination, and placement constraints.", "database", ["memory_interface"]),
    step("signal_integrity", "SI", DESIGN_PHASE, BEFORE_PROTOTYPE, "Plan impedance, topology, length matching, and eye-margin risk.", "activity", ["signal_integrity"]),
    step("power_integrity", "PI", DESIGN_PHASE, BEFORE_PROTOTYPE, "Plan rails, decoupling, transient current, and PDN risk review.", "chart", ["power_integrity"]),
    step("stackup", "Stackup", DESIGN_PHASE, BEFORE_PROTOTYPE, "Recommend layer count, reference planes, and controlled impedance rules.", "board", ["stackup_planning", "impedance_control"]),
    step("timing_constraints", "Timing", TEST_PHASE, AFTER_PROTOTYPE, "Prepare timing constraints and interface validation checklist.", "report", ["timing_constraints"]),
  ], [
    ["eye_margin", "Eye Margin"], ["pdn_risk", "PDN Risk"], ["layer_count", "Layer Count"], ["interface_speed", "Interface Speed"], ["timing_risk", "Timing Risk"],
  ], [
    "Processor / FPGA Selection", "Memory Interface Plan", "SI / PI Risk Report", "Stackup Recommendation", "Impedance Rules", "Timing Constraint Notes",
  ]),
  placeholderPack("general_pcb", "General PCB", "General-purpose PCB planning, component inventory, connectors, assembly risk, layout constraints, and review package.", ["pcb", "controller board", "connectors", "leds", "header", "general", "board"], [
    step("requirements", "Requirements", DESIGN_PHASE, BEFORE_PROTOTYPE, "Extract board purpose, constraints, connectors, operating environment, and deliverables.", "file", ["requirements_capture"]),
    step("component_inventory", "Components", DESIGN_PHASE, BEFORE_PROTOTYPE, "List core ICs, passives, connectors, LEDs, protection, and programming hardware.", "chip", ["component_inventory"]),
    step("connector_io", "I/O Map", DESIGN_PHASE, BEFORE_PROTOTYPE, "Map connectors, LEDs, switches, programming headers, and board-level I/O.", "board", ["connector_planning"]),
    step("layout_constraints", "Layout", DESIGN_PHASE, BEFORE_PROTOTYPE, "Capture placement, assembly, DRC, connector access, and keep-out rules.", "board", ["layout_constraints"]),
    step("assembly_review", "Assembly", TEST_PHASE, AFTER_PROTOTYPE, "Review BOM availability, assembly risk, test points, and production notes.", "report", ["assembly_risk_review"]),
  ], [
    ["bom_cost", "BOM Cost"], ["layer_count", "Layer Count"], ["drc_risk", "DRC Risk"], ["assembly_risk", "Assembly Risk"], ["connector_count", "Connector Count"],
  ], [
    "Requirement Summary", "Component Inventory", "Connector / I/O Map", "Layout Constraint Set", "Assembly Risk Review", "Generated EE Package",
  ]),
];

export const DOMAIN_PACKS: Record<ProjectDomain, DomainPack> = packs.reduce(
  (acc, pack) => ({ ...acc, [pack.id]: pack }),
  {} as Record<ProjectDomain, DomainPack>,
);

export const DEMO_PROJECT_REQUESTS: DemoProjectRequest[] = [
  {
    id: "power_buck",
    label: "Power Electronics",
    request: "Design a vehicle/industrial 9-36 V to 5 V/3 A USB-C buck charger.",
  },
  {
    id: "rf_embedded_sensor",
    label: "RF / Embedded",
    request: "Design a 2.4 GHz BLE wireless temperature sensor node powered by a coin cell.",
  },
  {
    id: "analog_sensor",
    label: "Analog / Sensor",
    request: "Design a low-noise thermocouple measurement front-end with ADC output.",
  },
  {
    id: "high_speed",
    label: "High-Speed Digital",
    request: "Design an FPGA board with DDR memory and USB 3.0 interface.",
  },
  {
    id: "general_pcb",
    label: "General PCB",
    request: "Design a small controller board with connectors, LEDs, and a programming header.",
  },
];

function module(
  id: string,
  name: string,
  description: string,
  statusCategory: ModuleStatusCategory,
  domain: ProjectDomain,
  reason: string,
  inputArtifacts: string[],
  outputArtifacts: string[],
  icon: string,
  appearsInWorkflow = true,
): CapabilityModule {
  return { id, name, description, statusCategory, domain, reason, inputArtifacts, outputArtifacts, icon, appearsInWorkflow };
}

function metric(
  id: string,
  label: string,
  description: string,
  domain: ProjectDomain,
  backendMetricKey: string | undefined,
  pendingLabel: string,
): MetricDefinition {
  return { id, label, description, domain, backendMetricKey, pendingLabel };
}

function artifact(
  id: string,
  label: string,
  description: string,
  domain: ProjectDomain,
  sourceStageIds: string[],
  statusLabel: string,
): ArtifactDefinition {
  return { id, label, description, domain, sourceStageIds, statusLabel };
}

function step(
  id: string,
  title: string,
  phase: string,
  contextLabel: string,
  description: string,
  icon: string,
  moduleIds: string[],
): WorkflowStep {
  return { id, title, phase, contextLabel, description, icon, moduleIds, sourceStageIds: [] };
}

function placeholderPack(
  id: ProjectDomain,
  name: string,
  description: string,
  classifierHints: string[],
  workflowSteps: WorkflowStep[],
  metricRows: Array<[string, string]>,
  artifactLabels: string[],
): DomainPack {
  const capabilities = Array.from(new Set(workflowSteps.flatMap((workflowStep) => workflowStep.moduleIds))).map((moduleId, index) => {
    const workflowStep = workflowSteps.find((item) => item.moduleIds.includes(moduleId));
    const category: ModuleStatusCategory = index < 3 ? "required" : index < 5 ? "recommended" : "optional";
    return module(
      moduleId,
      titleFromId(moduleId),
      `${workflowStep?.title || "Module"} planning placeholder for the ${name} domain pack.`,
      category,
      id,
      category === "required"
        ? "Selected because the request strongly matches this domain."
        : "Recommended as a review or planning step for this domain.",
      ["Project request", "Classified domain pack"],
      [workflowStep?.title || "Planning output"],
      workflowStep?.icon || "file",
    );
  });
  return {
    id,
    name,
    description,
    classifierHints,
    uiLabels: {
      workflowTitle: "Selected Workflow",
      workflowSubtitle: `${name} pack is selected from request keywords. Placeholder modules show intended workflow coverage only.`,
      packageTitle: "Generated EE Package",
    },
    workflowSteps,
    capabilities,
    metrics: metricRows.map(([metricId, label]) =>
      metric(metricId, label, `${label} placeholder for the ${name} domain pack.`, id, undefined, "Estimate pending"),
    ),
    artifacts: artifactLabels.map((label, index) =>
      artifact(
        slug(label),
        label,
        `${label} placeholder artifact for the ${name} workflow.`,
        id,
        [workflowSteps[Math.min(index, workflowSteps.length - 1)]?.id || ""],
        "placeholder / not connected",
      ),
    ),
    placeholder: true,
  };
}

function titleFromId(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function slug(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}

function scorePack(pack: DomainPack, request: string): number {
  return pack.classifierHints.reduce((score, hint) => score + (request.includes(hint) ? 1 : 0), 0);
}

function inferProductType(request: string, domains: ProjectDomain[]): string {
  if (domains.includes("power_electronics") && (request.includes("buck") || request.includes("step-down"))) return "dc_dc_buck_converter";
  if (domains.includes("rf_communication") && domains.includes("embedded_mcu")) return "wireless_sensor_node";
  if (domains.includes("analog_sensor") && request.includes("thermocouple")) return "thermocouple_measurement_front_end";
  if (domains.includes("high_speed_digital") && request.includes("fpga")) return "fpga_high_speed_io_board";
  if (domains.includes("embedded_mcu")) return "embedded_controller_board";
  return "general_ee_pcb";
}

function mergeModules(packsToMerge: DomainPack[]): ModuleSelectionResult {
  const byId = new Map<string, CapabilityModule>();
  for (const pack of packsToMerge) {
    for (const item of pack.capabilities) {
      const existing = byId.get(item.id);
      if (!existing || rankCategory(item.statusCategory) < rankCategory(existing.statusCategory)) {
        byId.set(item.id, item);
      }
    }
  }
  const all = Array.from(byId.values());
  return {
    required: all.filter((item) => item.statusCategory === "required"),
    recommended: all.filter((item) => item.statusCategory === "recommended"),
    optional: all.filter((item) => item.statusCategory === "optional"),
    disabled: all.filter((item) => item.statusCategory === "disabled"),
  };
}

function rankCategory(category: ModuleStatusCategory): number {
  return { required: 0, recommended: 1, optional: 2, disabled: 3 }[category];
}

function groupWorkflowSections(steps: WorkflowStep[]): WorkflowSection[] {
  const sections: WorkflowSection[] = [];
  for (const workflowStep of steps) {
    const current = sections.find((section) => section.label === workflowStep.phase && section.contextLabel === workflowStep.contextLabel);
    if (current) {
      current.steps.push(workflowStep);
    } else {
      sections.push({ label: workflowStep.phase, contextLabel: workflowStep.contextLabel, steps: [workflowStep] });
    }
  }
  return sections;
}

function uniqueById<T extends { id: string }>(items: T[]): T[] {
  const seen = new Set<string>();
  return items.filter((item) => {
    if (seen.has(item.id)) return false;
    seen.add(item.id);
    return true;
  });
}

export function planWorkflow(requestText: string): WorkflowPlan {
  const normalized = requestText.toLowerCase();
  const scored = packs
    .map((pack) => ({ pack, score: scorePack(pack, normalized) }))
    .filter(({ score, pack }) => score > 0 && pack.id !== "general_pcb")
    .sort((a, b) => b.score - a.score);
  const selectedPacks = scored.length
    ? scored.slice(0, 2).map(({ pack }) => pack)
    : [DOMAIN_PACKS.general_pcb];
  const domains = selectedPacks.map((pack) => pack.id);
  const primaryDomain = selectedPacks[0]?.id || "general_pcb";
  const maxScore = scored[0]?.score || 0;
  const confidence = maxScore >= 3 ? "high" : maxScore >= 1 ? "medium" : "low";
  const productType = inferProductType(normalized, domains);
  const reasons = selectedPacks.map((pack) =>
    pack.placeholder
      ? `${pack.name} selected by keyword rules; modules are placeholder/config-driven.`
      : `${pack.name} selected by keyword rules; executable power demo modules are available.`,
  );
  const workflowSteps = uniqueById(selectedPacks.flatMap((pack) => pack.workflowSteps));
  const metrics = uniqueById(selectedPacks.flatMap((pack) => pack.metrics)).slice(0, 10);
  const artifacts = uniqueById(selectedPacks.flatMap((pack) => pack.artifacts));
  return {
    requestText,
    classification: {
      primaryDomain,
      domains,
      productType,
      confidence,
      reasons,
      source: "deterministic_keyword_rules",
    },
    selectedPacks,
    workflowSteps,
    workflowSections: groupWorkflowSections(workflowSteps),
    modules: mergeModules(selectedPacks),
    metrics,
    artifacts,
    capabilityNotice: selectedPacks.some((pack) => pack.placeholder)
      ? "Non-power domain packs are planning placeholders. They do not run real solvers or external integrations yet."
      : "Power Electronics is the first executable domain pack. Several outputs are still demo data or not-connected adapters.",
  };
}

export function validateWorkflowPlannerSamples(): string[] {
  const failures: string[] = [];
  const expected: Record<string, ProjectDomain[]> = {
    power_buck: ["power_electronics"],
    rf_embedded_sensor: ["rf_communication", "embedded_mcu"],
    analog_sensor: ["analog_sensor"],
    high_speed: ["high_speed_digital"],
    general_pcb: ["general_pcb"],
  };
  for (const sample of DEMO_PROJECT_REQUESTS) {
    const plan = planWorkflow(sample.request);
    const expectedDomains = expected[sample.id] || [];
    for (const domain of expectedDomains) {
      if (!plan.classification.domains.includes(domain)) {
        failures.push(`${sample.id} did not include ${domain}`);
      }
    }
    if (!plan.workflowSteps.length) failures.push(`${sample.id} produced no workflow steps`);
    if (!plan.metrics.length) failures.push(`${sample.id} produced no metrics`);
    if (!plan.artifacts.length) failures.push(`${sample.id} produced no artifacts`);
    const sectionLabels = plan.workflowSections.map((section) => section.label);
    const unexpectedSections = sectionLabels.filter((label) => label !== DESIGN_PHASE && label !== TEST_PHASE);
    if (unexpectedSections.length) {
      failures.push(`${sample.id} produced non-standard sections: ${unexpectedSections.join(", ")}`);
    }
    if (!sectionLabels.includes(DESIGN_PHASE) || !sectionLabels.includes(TEST_PHASE)) {
      failures.push(`${sample.id} did not produce the standard Design/Test sections`);
    }
  }
  return failures;
}
