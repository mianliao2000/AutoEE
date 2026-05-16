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

export interface WorkflowModule {
  id: string;
  name: string;
  phase: "design" | "test";
  status?: "pending" | "ready" | "running" | "completed" | "verified" | "needs_review" | "failed" | "locked" | "outdated";
  description?: string;
  outputArtifacts?: string[];
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
  phase?: "design" | "test";
  sourceStageIds: string[];
  statusLabel: string;
}

export interface DomainPack {
  id: ProjectDomain;
  label: string;
  name: string;
  demoProjectTitle: string;
  productType: string;
  description: string;
  classifierHints: string[];
  uiLabels: {
    workflowTitle: string;
    workflowSubtitle: string;
    packageTitle: string;
  };
  workflowSteps: WorkflowStep[];
  designModules: WorkflowModule[];
  testModules: WorkflowModule[];
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
const DEMO_DESIGN_STAGE_IDS = ["understand_specs", "select_parts", "loss_thermal", "waveforms", "control", "package"];
const DEMO_TEST_STAGE_IDS = ["embedded_coding_download", "closed_loop_tuning", "efficiency_logging", "test_report"];

const powerWorkflow: WorkflowStep[] = [
  {
    id: "requirements",
    title: "Requirement",
    phase: "Design",
    contextLabel: "Before PCB Prototype Fabrication",
    description: "Translate the product request into electrical targets, acceptance limits, and a plan for the design run.",
    icon: "file",
    sourceStageIds: ["understand_specs"],
    moduleIds: ["specs_parser"],
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
    id: "bom",
    title: "BOM",
    phase: "Design",
    contextLabel: "Before PCB Prototype Fabrication",
    description: "Select and review the component set before schematic and PCB layout work.",
    icon: "chip",
    sourceStageIds: ["select_parts"],
    moduleIds: ["component_selection", "topology_selection"],
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
    id: "review",
    title: "Review",
    phase: "Design",
    contextLabel: "Before PCB Prototype Fabrication",
    description: "Review design package readiness before prototype fabrication.",
    icon: "report",
    sourceStageIds: ["package", "test_report"],
    moduleIds: ["report_generation"],
  },
  {
    id: "firmware_control_code",
    title: "Firmware / Control Code",
    phase: "Test",
    contextLabel: "After PCB Prototype Returns",
    description: "Build firmware, flash the returned board, and record bring-up logs.",
    icon: "code",
    sourceStageIds: ["embedded_coding_download"],
    moduleIds: ["firmware_bringup"],
  },
  {
    id: "bench_bringup",
    title: "Bench Bring-Up",
    phase: "Test",
    contextLabel: "After PCB Prototype Returns",
    description: "Power the returned board, verify rails, identity, instrumentation, and safe startup.",
    icon: "activity",
    sourceStageIds: ["embedded_coding_download"],
    moduleIds: ["bench_bringup"],
  },
  {
    id: "tuning",
    title: "Tuning",
    phase: "Test",
    contextLabel: "After PCB Prototype Returns",
    description: "Run a bench tuning sweep and select control parameters.",
    icon: "sliders",
    sourceStageIds: ["closed_loop_tuning"],
    moduleIds: ["bench_loop_tuning"],
  },
  {
    id: "measurement_data",
    title: "Measurement Data",
    phase: "Test",
    contextLabel: "After PCB Prototype Returns",
    description: "Record efficiency, ripple, thermal, and instrument data.",
    icon: "database",
    sourceStageIds: ["efficiency_logging"],
    moduleIds: ["bench_data_logging"],
  },
  {
    id: "test_report",
    title: "Test Report",
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
    label: "Power / Energy",
    name: "Power / Energy",
    demoProjectTitle: "15W USB-C Buck Charger",
    productType: "DC/DC Buck Converter",
    description: "DC/DC converters, chargers, rails, power stages, loss/thermal checks, control, and power-layout review.",
    classifierHints: ["buck", "boost", "converter", "charger", "dc-dc", "usb-c", "vin", "vout", "5v", "12v", "24v", "36v", "amp", "power supply"],
    uiLabels: {
      workflowTitle: "Selected Workflow",
      workflowSubtitle: "Power electronics pack: design before fabrication, then test after the prototype returns.",
      packageTitle: "Generated Hardware Package",
    },
    workflowSteps: powerWorkflow,
    designModules: workflowModulesFromSteps(powerWorkflow, "Design"),
    testModules: workflowModulesFromSteps(powerWorkflow, "Test"),
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
      artifact("constraint_matrix", "Constraint Matrix", "Voltage, current, ripple, transient, efficiency, and thermal targets.", "power_electronics", ["understand_specs"], "deterministic estimate", "design"),
      artifact("buck_analysis_report", "Buck Analysis Report", "Formula-based buck calculations, equations, and analysis plots.", "power_electronics", ["loss_thermal"], "analysis artifact", "design"),
      artifact("simulation_waveforms", "Simulation Waveforms", "Circuit simulation or mock-adapter waveform artifacts.", "power_electronics", ["waveforms"], "adapter output", "design"),
      artifact("initial_bom", "Initial BOM", "First-pass selected parts with source labels.", "power_electronics", ["select_parts"], "fake distributor data", "design"),
      artifact("power_layout_rules", "Power Layout Rules", "Hot-loop, PDN, EMI, and manufacturing constraints.", "power_electronics", ["package"], "placeholder plan", "design"),
      artifact("review_report", "Review Report", "Design package, risks, missing evidence, and next actions.", "power_electronics", ["package"], "review draft", "design"),
      artifact("firmware_control_notes", "Firmware / Control Notes", "Firmware target, control code notes, and flash transcript.", "power_electronics", ["embedded_coding_download"], "demo bench data", "test"),
      artifact("bench_bringup_log", "Bench Bring-Up Log", "Prototype rail checks and safe-start notes.", "power_electronics", ["embedded_coding_download"], "demo bench data", "test"),
      artifact("tuning_record", "Tuning Record", "Closed-loop sweep and selected parameters.", "power_electronics", ["closed_loop_tuning"], "demo bench data", "test"),
      artifact("measured_waveforms", "Measured Waveforms", "Bench ripple, transient, temperature, and efficiency captures.", "power_electronics", ["efficiency_logging"], "demo bench data", "test"),
      artifact("final_test_report", "Final Test Report", "Post-prototype test conclusion and Rev B feedback.", "power_electronics", ["test_report"], "review draft", "test"),
    ],
    placeholder: false,
  },
  placeholderPack("rf_communication", "RF / Communication", "Wireless links, RF front-end choices, antennas, matching, RF layout, and compliance planning.", ["rf", "wireless", "ble", "bluetooth", "2.4 ghz", "wifi", "antenna", "lora", "zigbee"], [
    step("requirements", "Requirement", DESIGN_PHASE, BEFORE_PROTOTYPE, "Identify frequency band, range target, power limit, antenna needs, and compliance region.", "file", ["frequency_plan"]),
    step("rf_plan", "RF Plan", DESIGN_PHASE, BEFORE_PROTOTYPE, "Define radio architecture, channel assumptions, coexistence, and RF constraints.", "activity", ["rf_plan"]),
    step("link_budget", "Link Budget", DESIGN_PHASE, BEFORE_PROTOTYPE, "Estimate path loss, margin, transmit power, receiver sensitivity, and range risk.", "chart", ["link_budget"]),
    step("antenna_matching", "Antenna / Matching", DESIGN_PHASE, BEFORE_PROTOTYPE, "Select antenna approach and reserve matching-network strategy.", "activity", ["antenna_selection", "matching_network"]),
    step("pcb", "PCB", DESIGN_PHASE, BEFORE_PROTOTYPE, "Capture keep-outs, feedline, ground, antenna clearance, and RF layout rules.", "board", ["rf_layout_rules"]),
    step("rf_bringup", "RF Bring-Up", TEST_PHASE, AFTER_PROTOTYPE, "Power up the RF path and verify radio identity, clocks, and output enable.", "activity", ["rf_bringup"]),
    step("matching_tune", "Matching Tune", TEST_PHASE, AFTER_PROTOTYPE, "Tune antenna and matching network against VNA data.", "sliders", ["matching_tune"]),
    step("range_spectrum_data", "Range / Spectrum Data", TEST_PHASE, AFTER_PROTOTYPE, "Collect range, RSSI, spectrum, and occupied-bandwidth data.", "database", ["range_spectrum_data"]),
    step("compliance_precheck", "Compliance Pre-Check", TEST_PHASE, AFTER_PROTOTYPE, "Run pre-compliance checks before formal lab submission.", "report", ["compliance_precheck"]),
    step("rf_test_report", "RF Test Report", TEST_PHASE, AFTER_PROTOTYPE, "Generate RF test evidence and revision feedback.", "report", ["rf_test_report"]),
  ], [
    ["link_margin", "Link Margin"], ["range", "Range Estimate"], ["tx_power", "TX Power"], ["rx_sensitivity", "RX Sensitivity"], ["antenna_risk", "Antenna Risk"],
  ], [
    "Frequency Plan", "Link Budget", "Antenna / Matching Notes", "RF Layout Constraints", "Compliance Checklist", "VNA / Matching Data", "Spectrum Capture", "Range Test Data", "RF Test Report",
  ]),
  placeholderPack("analog_sensor", "Analog / Sensing", "Low-noise sensor interfaces, signal chains, ADC selection, noise budgets, calibration, and analog layout rules.", ["analog", "sensor", "thermocouple", "front-end", "adc", "op amp", "low-noise", "measurement"], [
    step("requirements", "Requirement", DESIGN_PHASE, BEFORE_PROTOTYPE, "Define sensor input, accuracy, bandwidth, calibration, and output requirements.", "file", ["requirements_capture"]),
    step("signal_chain", "Signal Chain", DESIGN_PHASE, BEFORE_PROTOTYPE, "Define the sensor, gain, filtering, ADC, reference, and calibration chain.", "activity", ["signal_chain_design"]),
    step("noise_error_budget", "Noise / Error Budget", DESIGN_PHASE, BEFORE_PROTOTYPE, "Estimate noise contributors, bandwidth, resolution, drift, and accuracy risk.", "chart", ["noise_analysis"]),
    step("components", "Components", DESIGN_PHASE, BEFORE_PROTOTYPE, "Shortlist amplifier, ADC, reference, protection, and filter components.", "chip", ["op_amp_selection", "adc_selection"]),
    step("schematic", "Schematic", DESIGN_PHASE, BEFORE_PROTOTYPE, "Prepare analog schematic decisions, guards, filtering, and references.", "file", ["schematic_plan"]),
    step("pcb", "PCB", DESIGN_PHASE, BEFORE_PROTOTYPE, "Capture grounding, guard, shielding, and sensitive-node layout rules.", "board", ["analog_layout_rules"]),
    step("review", "Review", DESIGN_PHASE, BEFORE_PROTOTYPE, "Review signal-chain evidence and signoff gaps.", "report", ["analog_review"]),
    step("calibration_script", "Calibration Script", TEST_PHASE, AFTER_PROTOTYPE, "Generate calibration script and production trim notes.", "code", ["calibration_plan"]),
    step("noise_measurement", "Noise Measurement", TEST_PHASE, AFTER_PROTOTYPE, "Collect measured input noise and bandwidth data.", "activity", ["noise_measurement"]),
    step("linearity_drift_data", "Linearity / Drift Data", TEST_PHASE, AFTER_PROTOTYPE, "Record gain, offset, linearity, and temperature drift measurements.", "database", ["linearity_drift_data"]),
    step("sensor_validation", "Sensor Validation", TEST_PHASE, AFTER_PROTOTYPE, "Validate sensor behavior against calibration references.", "activity", ["sensor_validation"]),
    step("test_report", "Test Report", TEST_PHASE, AFTER_PROTOTYPE, "Generate precision measurement test report and revision feedback.", "report", ["test_report"]),
  ], [
    ["noise", "Noise"], ["bandwidth", "Bandwidth"], ["resolution", "Resolution"], ["accuracy", "Accuracy"], ["drift_risk", "Drift Risk"],
  ], [
    "Signal Chain", "Sensor / ADC Selection", "Noise Budget", "Calibration Plan", "Analog Layout Rules", "Measured Noise Data", "Drift Data", "Test Report",
  ]),
  placeholderPack("embedded_mcu", "Embedded / IoT", "MCU/SoC selection, pin maps, firmware architecture, power modes, interfaces, debug, and manufacturing test.", ["mcu", "microcontroller", "firmware", "embedded", "coin cell", "battery", "gpio", "programming header", "sensor node"], [
    step("requirements", "Requirement", DESIGN_PHASE, BEFORE_PROTOTYPE, "Define sensors, radio, battery life, firmware, and board constraints.", "file", ["requirements_capture"]),
    step("architecture", "Architecture", DESIGN_PHASE, BEFORE_PROTOTYPE, "Define MCU/SoC architecture, sensors, power domains, and data flow.", "activity", ["architecture_plan"]),
    step("mcu_soc", "MCU / SoC", DESIGN_PHASE, BEFORE_PROTOTYPE, "Select the MCU or SoC class and resource envelope.", "chip", ["mcu_selection"]),
    step("firmware_plan", "Firmware Plan", DESIGN_PHASE, BEFORE_PROTOTYPE, "Plan tasks, drivers, telemetry, boot, update, and failure handling.", "code", ["firmware_architecture"]),
    step("embedded_power_budget", "Power Budget", DESIGN_PHASE, BEFORE_PROTOTYPE, "Estimate active and sleep current budget across modes.", "chart", ["power_budget"]),
    step("pcb", "PCB", DESIGN_PHASE, BEFORE_PROTOTYPE, "Capture layout, antenna, debug, battery, and manufacturing constraints.", "board", ["pcb_plan"]),
    step("review", "Review", DESIGN_PHASE, BEFORE_PROTOTYPE, "Review embedded design readiness and signoff gaps.", "report", ["embedded_review"]),
    step("firmware_build", "Firmware Build", TEST_PHASE, AFTER_PROTOTYPE, "Build firmware image and collect compile/programming logs.", "code", ["firmware_build"]),
    step("board_bringup", "Board Bring-Up", TEST_PHASE, AFTER_PROTOTYPE, "Verify power rails, clocks, debug access, and sensor identity.", "activity", ["board_bringup"]),
    step("power_profiling", "Power Profiling", TEST_PHASE, AFTER_PROTOTYPE, "Measure sleep, advertise, sample, and transmit current.", "chart", ["power_profiling"]),
    step("wireless_data_log", "Wireless / Data Log", TEST_PHASE, AFTER_PROTOTYPE, "Collect BLE link, range, packet, and sensor log data.", "database", ["wireless_data_log"]),
    step("test_report", "Test Report", TEST_PHASE, AFTER_PROTOTYPE, "Generate embedded test report and revision feedback.", "report", ["test_report"]),
  ], [
    ["battery_life", "Battery Life"], ["sleep_current", "Sleep Current"], ["io_usage", "I/O Usage"], ["firmware_risk", "Firmware Risk"], ["bom_cost", "BOM Cost"],
  ], [
    "MCU / SoC Selection", "Pin Map", "Firmware Architecture", "Power Budget", "Interface Map", "Firmware Build Log", "Power Profile", "Wireless Data Log", "Test Report",
  ]),
  placeholderPack("high_speed_digital", "High-Speed / Compute", "Processor or FPGA boards, DDR, USB/PCIe, signal integrity, power integrity, stackup, impedance, and timing constraints.", ["fpga", "ddr", "usb 3", "usb3", "pcie", "ethernet", "serdes", "memory", "impedance", "high-speed"], [
    step("requirements", "Requirement", DESIGN_PHASE, BEFORE_PROTOTYPE, "Define compute, memory, interface, timing, power, and stackup requirements.", "file", ["requirements_capture"]),
    step("architecture", "Architecture", DESIGN_PHASE, BEFORE_PROTOTYPE, "Select FPGA/processor class and high-speed interface assumptions.", "chip", ["processor_or_fpga_selection"]),
    step("power_tree", "Power Tree", DESIGN_PHASE, BEFORE_PROTOTYPE, "Plan rails, sequencing, PMIC choices, and transient current budget.", "chart", ["power_tree"]),
    step("interfaces", "Interfaces", DESIGN_PHASE, BEFORE_PROTOTYPE, "Define DDR, USB, PCIe, clocking, connectors, and termination strategy.", "database", ["memory_interface", "interfaces"]),
    step("si_pi", "SI / PI", DESIGN_PHASE, BEFORE_PROTOTYPE, "Plan impedance, topology, length matching, PDN, and eye-margin risk.", "activity", ["signal_integrity", "power_integrity"]),
    step("pcb", "PCB", DESIGN_PHASE, BEFORE_PROTOTYPE, "Recommend stackup, reference planes, controlled impedance, and routing rules.", "board", ["stackup_planning", "impedance_control"]),
    step("review", "Review", DESIGN_PHASE, BEFORE_PROTOTYPE, "Review high-speed design evidence and signoff gaps.", "report", ["timing_constraints"]),
    step("board_bringup", "Board Bring-Up", TEST_PHASE, AFTER_PROTOTYPE, "Verify rails, clocks, reset, and high-speed device identity.", "activity", ["board_bringup"]),
    step("firmware_jtag", "Firmware / JTAG", TEST_PHASE, AFTER_PROTOTYPE, "Program FPGA/processor and verify JTAG/debug access.", "code", ["firmware_jtag"]),
    step("eye_timing_data", "Eye / Timing Data", TEST_PHASE, AFTER_PROTOTYPE, "Collect eye-diagram-style timing and interface validation data.", "database", ["eye_timing_data"]),
    step("si_pi_validation", "SI / PI Validation", TEST_PHASE, AFTER_PROTOTYPE, "Validate SI/PI assumptions against measurements.", "activity", ["si_pi_validation"]),
    step("bringup_report", "Bring-Up Report", TEST_PHASE, AFTER_PROTOTYPE, "Generate high-speed bring-up report and revision feedback.", "report", ["bringup_report"]),
  ], [
    ["eye_margin", "Eye Margin"], ["pdn_risk", "PDN Risk"], ["layer_count", "Layer Count"], ["interface_speed", "Interface Speed"], ["timing_risk", "Timing Risk"],
  ], [
    "Processor / FPGA Selection", "Memory Interface Plan", "SI / PI Risk Report", "Stackup Recommendation", "Impedance Rules", "Eye / Timing Data", "SI / PI Validation", "Bring-Up Report",
  ]),
  placeholderPack("general_pcb", "General PCB / Interconnect", "General-purpose PCB planning, component inventory, connectors, assembly risk, layout constraints, and review package.", ["pcb", "controller board", "connectors", "leds", "header", "general", "board"], [
    step("requirements", "Requirement", DESIGN_PHASE, BEFORE_PROTOTYPE, "Extract board purpose, constraints, connectors, operating environment, and deliverables.", "file", ["requirements_capture"]),
    step("architecture", "Architecture", DESIGN_PHASE, BEFORE_PROTOTYPE, "Define controller, connectors, power entry, indicators, and debug architecture.", "activity", ["architecture_plan"]),
    step("bom", "BOM", DESIGN_PHASE, BEFORE_PROTOTYPE, "List core ICs, passives, connectors, LEDs, protection, and programming hardware.", "chip", ["component_inventory"]),
    step("schematic", "Schematic", DESIGN_PHASE, BEFORE_PROTOTYPE, "Map connectors, LEDs, switches, programming headers, and board-level I/O.", "file", ["schematic_plan"]),
    step("pcb", "PCB", DESIGN_PHASE, BEFORE_PROTOTYPE, "Capture placement, assembly, DRC, connector access, and keep-out rules.", "board", ["layout_constraints"]),
    step("drc_review", "DRC / Review", DESIGN_PHASE, BEFORE_PROTOTYPE, "Review DRC, ERC, BOM, assembly, and manufacturing readiness.", "report", ["assembly_risk_review"]),
    step("assembly_check", "Assembly Check", TEST_PHASE, AFTER_PROTOTYPE, "Inspect assembled prototype for polarity, placement, solder, and labeling issues.", "activity", ["assembly_check"]),
    step("continuity_pin_test", "Continuity / Pin Test", TEST_PHASE, AFTER_PROTOTYPE, "Verify connectors, pinout, continuity, shorts, and test points.", "activity", ["continuity_pin_test"]),
    step("functional_test_data", "Functional Test Data", TEST_PHASE, AFTER_PROTOTYPE, "Collect smoke-test and basic functional data.", "database", ["functional_test_data"]),
    step("manufacturing_notes", "Manufacturing Notes", TEST_PHASE, AFTER_PROTOTYPE, "Capture DFM, fixture, assembly, silkscreen, and next-build notes.", "report", ["manufacturing_notes"]),
    step("test_report", "Test Report", TEST_PHASE, AFTER_PROTOTYPE, "Generate controller-board test report and revision feedback.", "report", ["test_report"]),
  ], [
    ["bom_cost", "BOM Cost"], ["layer_count", "Layer Count"], ["drc_risk", "DRC Risk"], ["assembly_risk", "Assembly Risk"], ["connector_count", "Connector Count"],
  ], [
    "Requirement Summary", "Component Inventory", "Connector / I/O Map", "Layout Constraint Set", "Assembly Risk Review", "Continuity Test Data", "Manufacturing Notes", "Test Report",
  ]),
];

export const DOMAIN_PACKS: Record<ProjectDomain, DomainPack> = packs.reduce(
  (acc, pack) => ({ ...acc, [pack.id]: pack }),
  {} as Record<ProjectDomain, DomainPack>,
);

export const DEMO_PROJECT_REQUESTS: DemoProjectRequest[] = [
  {
    id: "power_buck",
    label: "Power / Energy",
    request: "Design a vehicle/industrial 9-36 V to 5 V/3 A USB-C buck charger.",
  },
  {
    id: "embedded_iot",
    label: "Embedded / IoT",
    request: "Design a low-power embedded IoT sensor node with an MCU, coin-cell battery, sensor interface, and firmware plan.",
  },
  {
    id: "rf_communication",
    label: "RF / Communication",
    request: "Design a 2.4 GHz RF communication link with antenna matching and range validation.",
  },
  {
    id: "analog_sensor",
    label: "Analog / Sensing",
    request: "Design a low-noise thermocouple measurement front-end with ADC output.",
  },
  {
    id: "high_speed",
    label: "High-Speed / Compute",
    request: "Design an FPGA board with DDR memory and USB 3.0 interface.",
  },
  {
    id: "general_pcb",
    label: "General PCB / Interconnect",
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
  phase: "design" | "test" = "design",
): ArtifactDefinition {
  return { id, label, description, domain, phase, sourceStageIds, statusLabel };
}

function step(
  id: string,
  title: string,
  phase: string,
  contextLabel: string,
  description: string,
  icon: string,
  moduleIds: string[],
  sourceStageIds: string[] = [],
): WorkflowStep {
  return { id, title, phase, contextLabel, description, icon, moduleIds, sourceStageIds };
}

function mapPlaceholderWorkflowToDemoStages(workflowSteps: WorkflowStep[]): WorkflowStep[] {
  return workflowSteps.map((workflowStep) => {
    if (workflowStep.sourceStageIds.length) return workflowStep;
    return { ...workflowStep, sourceStageIds: [workflowStep.id] };
  });
}

function workflowModulesFromSteps(workflowSteps: WorkflowStep[], phase: "Design" | "Test"): WorkflowModule[] {
  const normalizedPhase = phase === "Design" ? "design" : "test";
  return workflowSteps
    .filter((workflowStep) => workflowStep.phase === phase)
    .map((workflowStep) => ({
      id: workflowStep.id,
      name: workflowStep.title,
      phase: normalizedPhase,
      status: normalizedPhase === "design" ? "pending" : "locked",
      description: workflowStep.description,
      outputArtifacts: workflowStep.sourceStageIds,
    }));
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
  const mappedWorkflowSteps = mapPlaceholderWorkflowToDemoStages(workflowSteps);
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
    label: name,
    name,
    demoProjectTitle: demoTitleForDomain(id),
    productType: productTypeForDomain(id),
    description,
    classifierHints,
    uiLabels: {
      workflowTitle: "Selected Workflow",
      workflowSubtitle: `${name} pack is selected from request keywords. Placeholder modules show intended workflow coverage only.`,
      packageTitle: "Generated Hardware Package",
    },
    workflowSteps: mappedWorkflowSteps,
    designModules: workflowModulesFromSteps(mappedWorkflowSteps, "Design"),
    testModules: workflowModulesFromSteps(mappedWorkflowSteps, "Test"),
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
        mappedWorkflowSteps[Math.min(index, mappedWorkflowSteps.length - 1)]?.sourceStageIds || [],
        "placeholder / not connected",
        mappedWorkflowSteps[Math.min(index, mappedWorkflowSteps.length - 1)]?.phase === "Test" ? "test" : "design",
      ),
    ),
    placeholder: true,
  };
}

function demoTitleForDomain(id: ProjectDomain): string {
  const labels: Record<ProjectDomain, string> = {
    power_electronics: "15W USB-C Buck Charger",
    rf_communication: "2.4 GHz RF Communication Link",
    analog_sensor: "Low-Noise Thermocouple Front-End",
    embedded_mcu: "BLE Wireless Sensor Node",
    high_speed_digital: "FPGA Board with DDR and USB 3.0",
    general_pcb: "Small Controller Board",
  };
  return labels[id];
}

function productTypeForDomain(id: ProjectDomain): string {
  const labels: Record<ProjectDomain, string> = {
    power_electronics: "DC/DC Buck Converter",
    rf_communication: "RF Communication System",
    analog_sensor: "Precision Sensor Front-End",
    embedded_mcu: "Embedded IoT Controller",
    high_speed_digital: "High-Speed Compute Board",
    general_pcb: "General Controller PCB",
  };
  return labels[id];
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
  return "general_hardware_pcb";
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
  const forceGeneralPcb = normalized.includes("controller board")
    && (normalized.includes("connectors") || normalized.includes("leds") || normalized.includes("programming header"));
  const scored = packs
    .map((pack) => ({ pack, score: scorePack(pack, normalized) }))
    .filter(({ score, pack }) => score > 0 && pack.id !== "general_pcb")
    .sort((a, b) => b.score - a.score);
  const selectedPacks = forceGeneralPcb
    ? [DOMAIN_PACKS.general_pcb]
    : scored.length
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
    embedded_iot: ["embedded_mcu"],
    rf_communication: ["rf_communication"],
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
    if (plan.workflowSteps.some((workflowStep) => !workflowStep.sourceStageIds.length)) {
      failures.push(`${sample.id} produced workflow steps without demo status source mapping`);
    }
    if (plan.artifacts.some((artifactItem) => !artifactItem.sourceStageIds.length)) {
      failures.push(`${sample.id} produced artifacts without demo status source mapping`);
    }
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
