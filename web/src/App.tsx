import React from "react";
import { DEMO_PROJECT_REQUESTS, planWorkflow, validateWorkflowPlannerSamples } from "./domain/workflow";
import type { ArtifactDefinition, CapabilityModule, MetricDefinition, WorkflowPlan, WorkflowStep } from "./domain/workflow";

type AnyRecord = Record<string, any>;

const EMPTY_STATE: AnyRecord = {
  prompt: "Design a vehicle/industrial 9-36V to 5V/3A USB-C buck charger.",
  workflowStatus: "loading",
  running: false,
  stages: [],
  metrics: {},
  energy: { cards: [] },
  waveforms: { available: false, series: {}, limits: {}, metrics: {}, events: [], controlBode: { available: false, series: {}, metrics: {} } },
  lossThermal: { available: false, sweep: {}, pies: [], thermal: { componentTempsC: [] } },
  designRationale: { sections: [], formulas: [], risks: [], missingData: [], nextActions: [] },
  riskSummary: { risks: [], missingData: [], recommendedNextActions: [] },
  executionPlan: { available: false, items: [] },
  partsCatalog: { available: false, items: [] },
  analysisSummary: { available: false, cards: [] },
  controlPlan: { available: false, parameters: [], validation: [] },
  pcbAutomationPlan: { available: false, automationSteps: [] },
  testWorkflow: { available: false, cards: [] },
  fakeCapabilityNotices: [],
  evidenceBadges: [],
  progressEvents: [],
  rawState: {}
};
const DIY_REQUEST_FALLBACK = "Design a custom hardware project.";
const DEFAULT_PROJECT_REQUEST = DEMO_PROJECT_REQUESTS[0]?.request || EMPTY_STATE.prompt;

interface DemoCircuitProfile {
  id: string;
  projectName: string;
  circuitName: string;
  shortSummary: string;
  packageSummary: string;
  fakeNotice: string;
  detailTabs: string[];
  metrics: Record<string, AnyRecord>;
  circuitBlocks: string[];
  moduleResults: Record<string, { title: string; outputs: string[]; artifacts: string[]; status: string }>;
}

const DEMO_CIRCUIT_PROFILES: Record<string, DemoCircuitProfile> = {
  power_buck: {
    id: "power_buck",
    projectName: "USB-C Buck Charger",
    circuitName: "9-36 V to 5 V / 3 A synchronous buck converter",
    shortSummary: "Automotive input buck charger with power-stage, control, PCB, and post-prototype test flow.",
    packageSummary: "Power stage BOM, loss/thermal estimate, ripple/transient preview, control seed, PCB layout rules, and review report.",
    fakeNotice: "Executable power demo with mock distributors and synthetic/not-signoff evidence.",
    detailTabs: ["Waveforms", "Loss/Thermal", "Design Rationale", "Risk Summary", "Developer State"],
    metrics: {},
    circuitBlocks: ["Input protection", "Synchronous buck stage", "Inductor and output filter", "USB-C 5 V rail", "Control feedback", "Power-layout constraints"],
    moduleResults: {},
  },
  rf_embedded_sensor: {
    id: "rf_embedded_sensor",
    projectName: "BLE Temperature Sensor Node",
    circuitName: "2.4 GHz coin-cell wireless temperature sensor node",
    shortSummary: "BLE SoC, low-power sensor front-end, chip antenna, matching network, coin-cell power tree, and manufacturing test hooks.",
    packageSummary: "Frequency plan, RF SoC shortlist, link budget, antenna/matching notes, firmware architecture, low-power budget, and compliance checklist.",
    fakeNotice: "Planning preview only. RF, antenna, firmware, and compliance adapters are not connected yet.",
    detailTabs: ["Link Budget / RF Plan", "Firmware & Power Budget", "Risk Summary", "Developer State"],
    metrics: {
      link_margin: { display: "14.8 dB", tone: "pass", target: "> 10 dB" },
      range: { display: "32 m indoor", tone: "neutral", target: "20 m" },
      tx_power: { display: "0 dBm", tone: "neutral" },
      rx_sensitivity: { display: "-96 dBm", tone: "pass" },
      antenna_risk: { display: "Medium", tone: "warn" },
      battery_life: { display: "14 mo est.", tone: "pass" },
      sleep_current: { display: "2.1 uA", tone: "pass" },
      io_usage: { display: "11 / 24 pins", tone: "neutral" },
      firmware_risk: { display: "Medium", tone: "warn" },
      bom_cost: { display: "$8.40", tone: "neutral" },
    },
    circuitBlocks: ["Coin-cell holder", "BLE SoC", "Temperature sensor", "32 MHz crystal", "Matching network", "Chip antenna", "SWD header", "Test pads"],
    moduleResults: {
      rf_requirements: {
        title: "RF requirement plan",
        outputs: ["2.4 GHz BLE peripheral", "Indoor range target: 20-30 m", "Coin-cell energy budget", "FCC/CE pre-scan checklist"],
        artifacts: ["frequency_plan.md", "wireless_requirements.json"],
        status: "Demo data / Not connected",
      },
      rf_ic_selection: {
        title: "RF SoC shortlist",
        outputs: ["Nordic nRF52-class BLE SoC", "Integrated DC/DC option", "SWD programming header", "I2C sensor interface"],
        artifacts: ["rf_soc_shortlist.csv", "pin_resource_map.json"],
        status: "Fake supplier shortlist",
      },
      link_budget: {
        title: "Link budget estimate",
        outputs: ["TX power: 0 dBm", "RX sensitivity: -96 dBm", "Estimated indoor link margin: 14.8 dB", "Antenna placement risk: medium"],
        artifacts: ["link_budget_demo.xlsx"],
        status: "First-order estimate",
      },
      antenna_matching: {
        title: "Antenna and matching plan",
        outputs: ["Chip antenna with keep-out", "Pi matching network reserved", "50 ohm feedline target", "Ground clearance rule"],
        artifacts: ["antenna_matching_notes.md"],
        status: "Placeholder RF plan",
      },
      rf_layout: {
        title: "RF layout constraints",
        outputs: ["Antenna edge placement", "Via fence around RF path", "No copper under antenna keep-out", "Short feedline route"],
        artifacts: ["rf_layout_rules.md"],
        status: "Layout rule draft",
      },
      wireless_compliance: {
        title: "Wireless compliance review",
        outputs: ["BLE advertising test", "Conducted power check", "Pre-scan radiated emissions", "Labeling and region notes"],
        artifacts: ["wireless_compliance_checklist.md"],
        status: "Review checklist",
      },
      mcu_selection: {
        title: "MCU resource plan",
        outputs: ["BLE SoC selected as MCU", "I2C sensor bus", "ADC battery monitor", "SWD debug path"],
        artifacts: ["mcu_resource_plan.json"],
        status: "Planning preview",
      },
      firmware_architecture: {
        title: "Firmware architecture",
        outputs: ["Sleep-first scheduler", "BLE advertising state machine", "Sensor sampling task", "Battery telemetry packet"],
        artifacts: ["firmware_architecture.md"],
        status: "Planning preview",
      },
      embedded_power_budget: {
        title: "Low-power budget",
        outputs: ["Sleep current: 2.1 uA", "Advertising burst: 6.8 mA", "Average current: 15 uA", "Battery estimate: 14 months"],
        artifacts: ["power_budget_demo.csv"],
        status: "Demo estimate",
      },
      manufacturing_test: {
        title: "Manufacturing test plan",
        outputs: ["SWD programming", "Current profile check", "BLE RSSI smoke test", "Sensor calibration point"],
        artifacts: ["manufacturing_test_plan.md"],
        status: "Test preview",
      },
    },
  },
  analog_sensor: {
    id: "analog_sensor",
    projectName: "Thermocouple Measurement Front-End",
    circuitName: "Low-noise thermocouple amplifier with ADC output",
    shortSummary: "Sensor protection, instrumentation amplifier, cold-junction measurement, low-pass filter, precision reference, and ADC interface.",
    packageSummary: "Signal-chain plan, sensor/protection selection, op-amp and ADC shortlist, noise budget, calibration plan, and analog layout rules.",
    fakeNotice: "Planning preview only. Noise simulation, calibration fixtures, and analog validation are not connected yet.",
    detailTabs: ["Signal Chain", "Noise Budget", "Calibration Plan", "Risk Summary", "Developer State"],
    metrics: {
      noise: { display: "1.8 uVrms", tone: "pass", target: "< 2.5 uVrms" },
      bandwidth: { display: "12 Hz", tone: "neutral" },
      resolution: { display: "0.08 C", tone: "pass" },
      accuracy: { display: "+/-0.6 C", tone: "warn" },
      drift_risk: { display: "Medium", tone: "warn" },
    },
    circuitBlocks: ["Thermocouple input", "ESD/filter network", "Instrumentation amplifier", "Cold-junction sensor", "Precision reference", "24-bit ADC", "SPI/I2C output"],
    moduleResults: {
      signal_chain: {
        title: "Signal-chain draft",
        outputs: ["Type-K thermocouple input", "Gain stage before ADC", "Cold-junction compensation sensor", "Anti-alias low-pass filter"],
        artifacts: ["signal_chain_block_diagram.md"],
        status: "Planning preview",
      },
      sensor_selection: {
        title: "Sensor and protection",
        outputs: ["Thermocouple terminal block", "Low-leakage ESD clamp", "RC input filter", "Open-sensor detection path"],
        artifacts: ["sensor_input_notes.md"],
        status: "Demo data / Not connected",
      },
      op_amp_adc: {
        title: "Amplifier and ADC shortlist",
        outputs: ["Zero-drift instrumentation amplifier", "24-bit delta-sigma ADC", "2.5 V precision reference", "Low-noise LDO"],
        artifacts: ["analog_bom_shortlist.csv"],
        status: "Fake supplier shortlist",
      },
      noise_budget: {
        title: "Noise budget",
        outputs: ["Input noise estimate: 1.8 uVrms", "Effective resolution: 0.08 C", "Bandwidth: 12 Hz", "Dominant risk: offset drift"],
        artifacts: ["noise_budget_demo.xlsx"],
        status: "First-order estimate",
      },
      analog_layout: {
        title: "Analog layout constraints",
        outputs: ["Guard sensitive input nodes", "Split noisy digital return path", "Kelvin reference routing", "Thermal symmetry around CJC sensor"],
        artifacts: ["analog_layout_rules.md"],
        status: "Layout rule draft",
      },
      calibration: {
        title: "Calibration plan",
        outputs: ["Two-point temperature calibration", "Cold-junction offset trim", "Open-sensor fault test", "Production coefficient storage"],
        artifacts: ["calibration_plan.md"],
        status: "Test preview",
      },
    },
  },
  high_speed: {
    id: "high_speed",
    projectName: "FPGA DDR / USB 3.0 Board",
    circuitName: "FPGA board with DDR memory and USB 3.0 interface",
    shortSummary: "FPGA fabric, DDR memory topology, USB 3.0 PHY, multi-rail power tree, controlled impedance stackup, and timing constraints.",
    packageSummary: "FPGA/DDR plan, memory topology, SI/PI risk review, stackup recommendation, impedance rules, and timing checklist.",
    fakeNotice: "Planning preview only. SI/PI solvers, FPGA tools, and layout engines are not connected yet.",
    detailTabs: ["SI / PI", "Stackup & Timing", "Risk Summary", "Developer State"],
    metrics: {
      eye_margin: { display: "22% UI", tone: "warn", target: "> 20% UI" },
      pdn_risk: { display: "Medium", tone: "warn" },
      layer_count: { display: "8 layers", tone: "neutral" },
      interface_speed: { display: "5 Gbps", tone: "neutral" },
      timing_risk: { display: "Medium", tone: "warn" },
    },
    circuitBlocks: ["FPGA", "DDR memory", "USB 3.0 PHY", "Clock tree", "PMIC rails", "8-layer stackup", "JTAG/debug", "High-speed connectors"],
    moduleResults: {
      processor_fpga: {
        title: "FPGA selection envelope",
        outputs: ["Mid-range FPGA class", "DDR-capable bank assignment", "USB 3.0 PHY interface", "JTAG and configuration memory"],
        artifacts: ["fpga_selection_envelope.md"],
        status: "Planning preview",
      },
      memory_interface: {
        title: "DDR topology",
        outputs: ["Point-to-point DDR interface", "Fly-by control/address plan", "Length-match groups", "Termination strategy"],
        artifacts: ["ddr_topology_plan.md"],
        status: "Placeholder SI plan",
      },
      signal_integrity: {
        title: "Signal integrity plan",
        outputs: ["USB 3.0 differential pair: 90 ohm", "DDR byte-lane matching", "Clock isolation", "Eye margin estimate: 22% UI"],
        artifacts: ["si_constraints.csv"],
        status: "First-order estimate",
      },
      power_integrity: {
        title: "Power integrity plan",
        outputs: ["Core rail transient target", "DDR VTT/VREF handling", "Decoupling placement classes", "PDN risk: medium"],
        artifacts: ["pdn_review_plan.md"],
        status: "Placeholder PI plan",
      },
      stackup: {
        title: "Stackup recommendation",
        outputs: ["8-layer stackup", "Adjacent solid reference planes", "Controlled impedance routing layers", "Return via rules"],
        artifacts: ["stackup_recommendation.md"],
        status: "Layout rule draft",
      },
      timing_constraints: {
        title: "Timing constraint checklist",
        outputs: ["DDR timing groups", "USB reference clock constraints", "CDC review", "Board delay export placeholder"],
        artifacts: ["timing_constraints_notes.md"],
        status: "Review checklist",
      },
    },
  },
  general_pcb: {
    id: "general_pcb",
    projectName: "Small Controller Board",
    circuitName: "General controller PCB with connectors, LEDs, and programming header",
    shortSummary: "MCU control board with regulated input, connector map, status LEDs, protection, programming header, and assembly/test notes.",
    packageSummary: "Requirement summary, component inventory, connector/I/O map, layout constraints, assembly risk review, and generated hardware package draft.",
    fakeNotice: "Planning preview only. Real schematic capture, layout, and assembly quoting are not connected yet.",
    detailTabs: ["Board Plan", "Component / I/O Map", "Assembly Review", "Risk Summary", "Developer State"],
    metrics: {
      bom_cost: { display: "$12.80", tone: "neutral" },
      layer_count: { display: "2 layers", tone: "pass" },
      drc_risk: { display: "Low", tone: "pass" },
      assembly_risk: { display: "Medium", tone: "warn" },
      connector_count: { display: "6", tone: "neutral" },
    },
    circuitBlocks: ["MCU", "5 V input", "3.3 V regulator", "I/O connectors", "Status LEDs", "Programming header", "ESD protection", "Test points"],
    moduleResults: {
      requirements: {
        title: "Board requirements",
        outputs: ["Small controller board", "Connectors and LEDs", "Programming header", "Low-cost assembly target"],
        artifacts: ["requirements_summary.md"],
        status: "Planning preview",
      },
      component_inventory: {
        title: "Component inventory",
        outputs: ["MCU", "3.3 V regulator", "Connector set", "LED indicators", "Protection passives"],
        artifacts: ["component_inventory.csv"],
        status: "Fake catalog data",
      },
      connector_io: {
        title: "Connector and I/O map",
        outputs: ["6 connector groups", "GPIO allocation", "Programming header pinout", "LED and button assignments"],
        artifacts: ["connector_io_map.json"],
        status: "Planning preview",
      },
      layout_constraints: {
        title: "Layout constraint set",
        outputs: ["2-layer board target", "Connector edge placement", "Test point access", "Assembly keep-outs"],
        artifacts: ["layout_constraints.md"],
        status: "Layout rule draft",
      },
      assembly_review: {
        title: "Assembly review",
        outputs: ["Through-hole connector risk", "LED polarity checks", "Programming jig access", "BOM availability review"],
        artifacts: ["assembly_review.md"],
        status: "Review checklist",
      },
    },
  },
};

const GROUP_COLORS: Record<string, string> = {
  MOSFET: "#7c8cff",
  Inductor: "#2f80ed",
  Capacitors: "#00b894",
  "PCB/PDN": "#f2b84b",
  Other: "#8a94a6"
};

function clsStatus(status: string | undefined): string {
  return `status ${String(status || "waiting").toLowerCase().replace(/_/g, "-")}`;
}

function titleCase(value: string | undefined): string {
  return String(value || "waiting")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function metricDisplay(metric: AnyRecord | undefined): string {
  if (!metric) return "Pending";
  const value = String(metric.display ?? metric.label ?? metric.value ?? "Pending");
  return value === "-" ? "Pending" : value;
}

async function postJson(path: string, body?: AnyRecord): Promise<AnyRecord> {
  const response = await fetch(path, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined
  });
  if (!response.ok) {
    let detail = "";
    try {
      detail = (await response.json()).detail;
    } catch {
      detail = "";
    }
    throw new Error(detail || `${path} failed with ${response.status}`);
  }
  return response.json();
}

function useAutoEEState() {
  const [state, setState] = React.useState<AnyRecord>(EMPTY_STATE);
  const [notice, setNotice] = React.useState("");

  React.useEffect(() => {
    let cancelled = false;
    fetch("/api/state")
      .then((response) => response.json())
      .then((payload) => {
        if (!cancelled) setState(payload);
      })
      .catch((error) => setNotice(`Backend state unavailable: ${error.message}`));

    const events = new EventSource("/api/events");
    events.addEventListener("state", (event) => {
      setState(JSON.parse((event as MessageEvent).data));
    });
    events.onerror = () => setNotice("Live event stream reconnecting...");
    return () => {
      cancelled = true;
      events.close();
    };
  }, []);

  const actions = {
    runDemo: async (context?: AnyRecord) => {
      setNotice("");
      setState((current: AnyRecord) => ({
        ...current,
        running: true,
        workflowStatus: "running",
        stages: (current.stages || []).map((stage: AnyRecord) => ({ ...stage, status: "waiting" })),
        activeDemoRequestId: context?.requestId ?? current.activeDemoRequestId,
        activeDemoDomain: context?.domain ?? current.activeDemoDomain,
        activeDemoProductType: context?.productType ?? current.activeDemoProductType,
        demoMode: context && context.domain !== "power_electronics" ? "profile_fake" : "power_backend",
        activeDemoStages: (context?.workflowSteps || []).map((step: AnyRecord) => ({
          id: step.id,
          title: step.title,
          phase: step.phase,
          status: "waiting",
        })),
        currentStage: null,
      }));
      try {
        const payload = await postJson("/api/run-demo", context);
        setState(payload.state);
      } catch (exc: any) {
        setNotice(`Run demo failed: ${exc.message}`);
      }
    },
    stop: async () => {
      try {
        const payload = await postJson("/api/stop");
        setState(payload.state);
      } catch (exc: any) {
        setNotice(`Stop failed: ${exc.message}`);
      }
    },
    reset: async () => {
      setNotice("");
      try {
        const payload = await postJson("/api/reset");
        setState(payload.state);
      } catch (exc: any) {
        setNotice(`Reset failed: ${exc.message}`);
      }
    },
    exportSnapshot: async () => {
      try {
        const payload = await postJson("/api/export-snapshot");
        setState(payload.state);
        setNotice(`Snapshot exported: ${payload.path}`);
      } catch (exc: any) {
        setNotice(`Export failed: ${exc.message}`);
      }
    },
    applySpec: async (spec: AnyRecord) => {
      setNotice("");
      const payload = await postJson("/api/spec", { spec });
      setState(payload.state);
      setNotice("Specs applied. Previous results were cleared.");
    }
  };

  return { state, notice, actions };
}

function StatusPill({ status }: { status: string }) {
  return <span className={clsStatus(status)}>{titleCase(status)}</span>;
}

function demoProfileForPlan(plan: WorkflowPlan): DemoCircuitProfile {
  const sampleId = selectedSampleId(plan.requestText);
  if (DEMO_CIRCUIT_PROFILES[sampleId]) return DEMO_CIRCUIT_PROFILES[sampleId];
  const primary = plan.classification.primaryDomain;
  if (primary === "rf_communication" || plan.classification.domains.includes("rf_communication")) return DEMO_CIRCUIT_PROFILES.rf_embedded_sensor;
  if (primary === "analog_sensor") return DEMO_CIRCUIT_PROFILES.analog_sensor;
  if (primary === "high_speed_digital") return DEMO_CIRCUIT_PROFILES.high_speed;
  if (primary === "general_pcb" || primary === "embedded_mcu") return DEMO_CIRCUIT_PROFILES.general_pcb;
  return DEMO_CIRCUIT_PROFILES.power_buck;
}

function validateDemoCircuitProfiles(): string[] {
  const failures: string[] = [];
  for (const sample of DEMO_PROJECT_REQUESTS) {
    const plan = planWorkflow(sample.request);
    const profile = demoProfileForPlan(plan);
    if (!profile) failures.push(`${sample.id} has no demo circuit profile`);
    if (!profile.detailTabs.length) failures.push(`${sample.id} has no domain detail tabs`);
    if (profile.id !== "power_buck" && profile.detailTabs.some((tab) => ["Waveforms", "Loss/Thermal"].includes(tab))) {
      failures.push(`${sample.id} exposes power-only tabs in a non-power profile`);
    }
  }
  return failures;
}

function demoRunPayload(plan: WorkflowPlan): AnyRecord {
  const profile = demoProfileForPlan(plan);
  return {
    requestId: profile.id,
    requestText: plan.requestText,
    domain: plan.classification.primaryDomain,
    productType: plan.classification.productType,
    workflowSteps: plan.workflowSteps.map((step) => ({
      id: step.id,
      title: step.title,
      phase: step.phase,
    })),
  };
}

function combinedStagePayloads(state: AnyRecord): AnyRecord[] {
  return [...(state.stages || []), ...(state.activeDemoStages || [])];
}

function aggregateStageStatus(stages: AnyRecord[], sourceIds: readonly string[]): string {
  const sourceStages = stages.filter((stage) => sourceIds.includes(stage.id));
  if (!sourceStages.length) return "waiting";
  const statuses = sourceStages.map((stage) => String(stage.status || "waiting"));
  if (statuses.some((status) => status === "running")) return "running";
  if (statuses.every((status) => status === "complete")) return "complete";
  if (statuses.some((status) => status === "complete" || status === "partial")) return "partial";
  if (statuses.some((status) => ["blocked", "error", "failed"].includes(status))) return "blocked";
  return "waiting";
}

function metricFromDefinition(definition: MetricDefinition, state: AnyRecord, plan?: WorkflowPlan): AnyRecord {
  const profileMetric = plan ? demoProfileForPlan(plan).metrics[definition.id] : undefined;
  if (profileMetric) {
    return { ...profileMetric, explain: definition.description };
  }
  const backendMetric = definition.backendMetricKey ? state.metrics?.[definition.backendMetricKey] : undefined;
  const display = metricDisplay(backendMetric);
  if (backendMetric && display !== "Pending") {
    return { ...backendMetric, display, explain: definition.description };
  }
  return {
    display: definition.pendingLabel || "Estimate pending",
    tone: "neutral",
    explain: definition.description,
  };
}

function sourceStatus(stages: AnyRecord[], sourceStageIds: readonly string[]): string {
  if (!sourceStageIds.length) return "waiting";
  return aggregateStageStatus(stages, sourceStageIds);
}

function domainName(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function RoadmapIcon({ name }: { name: string }) {
  const common = {
    width: 18,
    height: 18,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true
  };
  switch (name) {
    case "file":
      return (
        <svg {...common}>
          <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
          <path d="M14 3v5h5" />
          <path d="M8 13h8" />
          <path d="M8 17h5" />
        </svg>
      );
    case "chip":
      return (
        <svg {...common}>
          <rect x="7" y="7" width="10" height="10" rx="2" />
          <path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 15h3M1 9h3M1 15h3" />
        </svg>
      );
    case "chart":
      return (
        <svg {...common}>
          <path d="M4 19V5" />
          <path d="M4 19h16" />
          <path d="m7 15 3-4 3 2 4-7" />
        </svg>
      );
    case "activity":
      return (
        <svg {...common}>
          <path d="M3 12h4l2-6 4 12 2-6h6" />
        </svg>
      );
    case "sliders":
      return (
        <svg {...common}>
          <path d="M4 6h10M18 6h2M4 12h3M11 12h9M4 18h12M20 18h0" />
          <circle cx="16" cy="6" r="2" />
          <circle cx="9" cy="12" r="2" />
          <circle cx="18" cy="18" r="2" />
        </svg>
      );
    case "board":
      return (
        <svg {...common}>
          <rect x="4" y="4" width="16" height="16" rx="2" />
          <path d="M8 8h3v3H8z" />
          <path d="M15 8h1M15 12h1M8 16h8M11 9h3M11 10.5v4" />
        </svg>
      );
    case "code":
      return (
        <svg {...common}>
          <path d="m9 18-6-6 6-6" />
          <path d="m15 6 6 6-6 6" />
        </svg>
      );
    case "database":
      return (
        <svg {...common}>
          <ellipse cx="12" cy="5" rx="7" ry="3" />
          <path d="M5 5v6c0 1.7 3.1 3 7 3s7-1.3 7-3V5" />
          <path d="M5 11v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6" />
        </svg>
      );
    case "report":
      return (
        <svg {...common}>
          <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
          <path d="M14 3v5h5" />
          <path d="m9 15 2 2 4-5" />
        </svg>
      );
    default:
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="8" />
          <path d="M12 8v4l3 2" />
        </svg>
      );
  }
}

function statusDisplay(status: string): string {
  if (status === "active") return "Active";
  if (status === "complete") return "Done";
  if (status === "running") return "Running";
  if (status === "partial") return "Partial";
  if (["blocked", "error", "failed"].includes(status)) return "Blocked";
  return "";
}

function LeftRail({
  state,
  actions,
  notice,
  projectRequest,
  onProjectRequestChange,
  plan,
}: {
  state: AnyRecord;
  actions: AnyRecord;
  notice: string;
  projectRequest: string;
  onProjectRequestChange: (request: string) => void;
  plan: WorkflowPlan;
}) {
  const events = (state.progressEvents || []).slice(-8).reverse();
  const matchedSample = DEMO_PROJECT_REQUESTS.find((sample) => sample.request === projectRequest);
  const selectedSample = matchedSample ? matchedSample.id : "diy";
  const isDiyRequest = selectedSample === "diy";
  return (
    <aside className="leftRail">
      <div className="brandBlock">
        <div className="brandMark">AE</div>
        <div>
          <div className="brandTitle">AutoEE</div>
          <div className="brandSubtitle">AI Hardware Agent</div>
        </div>
      </div>

      <div className="promptCard">
        <div className="label">Product Request</div>
        {isDiyRequest ? (
          <textarea
            className="diyRequestInput"
            value={projectRequest}
            placeholder="Describe your hardware project request..."
            rows={4}
            onChange={(event) => onProjectRequestChange(event.target.value)}
          />
        ) : (
          <p>{projectRequest}</p>
        )}
        <label className="requestSelector">
          <span>Demo Request</span>
          <select
            value={selectedSample}
            onChange={(event) => {
              if (event.target.value === "diy") {
                onProjectRequestChange("");
                return;
              }
              const next = DEMO_PROJECT_REQUESTS.find((sample) => sample.id === event.target.value);
              if (next) onProjectRequestChange(next.request);
            }}
          >
            <option value="diy">DIY Request</option>
            {DEMO_PROJECT_REQUESTS.map((sample) => (
              <option value={sample.id} key={sample.id}>
                {sample.label}
              </option>
            ))}
          </select>
        </label>
        <small>
          Classified as {domainName(plan.classification.primaryDomain)} / {plan.classification.productType}
        </small>
      </div>

      <div className="buttonGrid">
        <button className="primary" onClick={() => actions.runDemo(demoRunPayload(plan))} disabled={state.running}>
          {state.running ? "Running..." : "Run Demo"}
        </button>
        <button onClick={actions.stop} disabled={!state.running}>
          Stop
        </button>
        <button onClick={actions.reset}>Reset Demo</button>
        <button onClick={actions.exportSnapshot}>Export Snapshot</button>
      </div>
      {notice && <div className="notice">{notice}</div>}

      <div className="railSection">
        <div className="sectionTitle">Founder Talk Track</div>
        <p className="talkTrack">
          {state.currentStage?.status === "complete"
            ? "Design package ready: show the generated artifacts, then be explicit about synthetic evidence and signoff gaps."
            : state.currentStage
              ? `${state.currentStage.title}: ${state.currentStage.plainEnglish}`
              : "Run the demo to show how AutoEE turns a product requirement into a reviewable design draft."}
        </p>
      </div>

      <div className="railSection grow">
        <div className="sectionTitle">Agent Log</div>
        <div className="eventList">
          {events.length ? (
            events.map((event: AnyRecord, index: number) => (
              <div className="eventItem" key={`${event.timestamp}-${index}`}>
                <span>{event.module_id}</span>
                <strong>{event.status}</strong>
                <p>{event.message}</p>
              </div>
            ))
          ) : (
            <div className="empty">Waiting for workflow events.</div>
          )}
        </div>
      </div>
    </aside>
  );
}

function Hero({ state, plan }: { state: AnyRecord; plan: WorkflowPlan }) {
  const heroMetrics = plan.metrics.slice(0, 4);
  return (
    <section className="hero">
      <div>
        <div className="eyebrow">AI-native modular hardware platform</div>
        <h1>Specification → Hardware Package</h1>
        <p>{plan.selectedPacks.map((pack) => pack.name).join(" + ")} workflow selected from the project request.</p>
      </div>
      <div className="productVision">
        <img src="/pcb-closeup-home.jpg" alt="PCB electronics close-up" />
        <div className="productVisionCaption">
          <strong>PCB Prototype All-in-One</strong>
        </div>
      </div>
      <div className="heroMetrics">
        {heroMetrics.map((metric) => (
          <MetricTile label={metric.label} metric={metricFromDefinition(metric, state, plan)} key={metric.id} />
        ))}
      </div>
    </section>
  );
}

function MetricTile({ label, metric }: { label: string; metric: AnyRecord }) {
  return (
    <div className={`metricTile tone-${metric?.tone || "neutral"}`}>
      <span>{label}</span>
      <strong>{metricDisplay(metric)}</strong>
      {metric?.target !== undefined && <small>Target {metric.target}</small>}
    </div>
  );
}

function ProjectUnderstanding({ plan }: { plan: WorkflowPlan }) {
  const profile = demoProfileForPlan(plan);
  return (
    <section className="panel understandingPanel">
      <div className="panelHeader">
        <div>
          <h2>Project Understanding</h2>
          <p>Domain classification and workflow scope for the current design.</p>
        </div>
      </div>
      <div className="understandingGrid">
        <div className="understandingPrimary">
          <span>Product Type</span>
          <strong>{plan.classification.productType.replace(/_/g, " ")}</strong>
          <small>{plan.classification.confidence} confidence / {plan.classification.source.replace(/_/g, " ")}</small>
        </div>
        <div className="domainPackList">
          {plan.selectedPacks.map((pack) => (
            <article className={pack.placeholder ? "placeholder" : ""} key={pack.id}>
              <span>{pack.placeholder ? "Placeholder pack" : "Executable pack"}</span>
              <strong>{pack.name}</strong>
              <p>{pack.description}</p>
            </article>
          ))}
        </div>
      </div>
      <ul className="reasonList">
        {plan.classification.reasons.map((reason) => <li key={reason}>{reason}</li>)}
      </ul>
      <div className="plannerNotice">{plan.capabilityNotice}</div>
      <div className="circuitDraftPanel">
        <div>
          <span>Generated Circuit Draft</span>
          <strong>{profile.circuitName}</strong>
          <p>{profile.shortSummary}</p>
          <small>{profile.fakeNotice}</small>
        </div>
        <ul>
          {profile.circuitBlocks.map((block) => <li key={block}>{block}</li>)}
        </ul>
      </div>
    </section>
  );
}

function CapabilityNotice({ payload }: { payload: AnyRecord }) {
  return (
    <div className="capabilityNotice">
      <strong>Demo data / Not connected</strong>
      <span>{payload.notice || "This module is using fake data. The real external capability is not connected yet."}</span>
      <small>
        {payload.sourceType || "demo_data"} / {payload.realCapabilityStatus || "not_connected"}
      </small>
    </div>
  );
}

function ExecutionPlanDetail({ data }: { data: AnyRecord }) {
  const items = data.items || [];
  if (!items.length) return <div className="empty">Run the demo to generate the execution plan.</div>;
  return (
    <div className="executionPlanGrid">
      {items.map((item: AnyRecord) => (
        <article className="executionPlanCard" key={item.step}>
          <div>
            <span>{item.step}</span>
            <strong>{item.goal}</strong>
          </div>
          <p>Inputs: {(item.inputs || []).join(", ")}</p>
          <p>Outputs: {(item.outputs || []).join(", ")}</p>
          <small>{item.nextIntegration}</small>
        </article>
      ))}
    </div>
  );
}

function PartsCatalogDetail({ data }: { data: AnyRecord }) {
  const items = data.items || [];
  if (!items.length) return <div className="empty">Run Parts to populate the fake DigiKey/Mouser BOM table.</div>;
  return (
    <div className="bomTableWrap">
      <div className="moduleMetricRow">
        <div><span>Total demo BOM</span><strong>${Number(data.totalCostUsd || 0).toFixed(2)}</strong></div>
        <div><span>Source</span><strong>Fake DigiKey + Mouser</strong></div>
      </div>
      <table className="bomTable">
        <thead>
          <tr>
            <th>Role</th>
            <th>Part</th>
            <th>Key Parameters</th>
            <th>Qty</th>
            <th>Price</th>
            <th>Links</th>
          </tr>
        </thead>
        <tbody>
          {items.map((part: AnyRecord) => (
            <tr key={part.role}>
              <td>{part.role}</td>
              <td><strong>{part.mpn}</strong><span>{part.manufacturer}</span></td>
              <td>{(part.keyParams || []).slice(0, 4).join("; ")}</td>
              <td>{part.quantity}</td>
              <td>${Number(part.lineTotalUsd || 0).toFixed(2)}</td>
              <td>
                <div className="linkList">
                  {part.datasheetUrl && <a href={part.datasheetUrl}>Datasheet</a>}
                  {part.supplierLinks?.digikey && <a href={part.supplierLinks.digikey}>DigiKey</a>}
                  {part.supplierLinks?.mouser && <a href={part.supplierLinks.mouser}>Mouser</a>}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AnalysisDetail({ data }: { data: AnyRecord }) {
  if (!data.available) return <div className="empty">Run Analysis to calculate loss and thermal estimates.</div>;
  return (
    <div>
      <div className="moduleMetricRow">
        {(data.cards || []).map((card: AnyRecord) => (
          <div key={card.label}><span>{card.label}</span><strong>{card.display}</strong></div>
        ))}
      </div>
      <div className="detailTwoCol">
        <section>
          <h4>Loss Terms</h4>
          <ul className="compactList">{(data.lossItems || []).slice(0, 8).map((item: AnyRecord) => <li key={item.label}>{item.label}: {item.display}</li>)}</ul>
        </section>
        <section>
          <h4>Thermal Notes</h4>
          <ul className="compactList">
            <li>Max junction estimate: {data.thermal?.maxJunctionTempC ? `${data.thermal.maxJunctionTempC} C` : "-"}</li>
            {(data.thermal?.warnings || []).map((item: string) => <li key={item}>{item}</li>)}
          </ul>
        </section>
      </div>
    </div>
  );
}

function ControlPlanDetail({ data }: { data: AnyRecord }) {
  if (!data.available) return <div className="empty">Run Control to generate the synthetic control plan.</div>;
  return (
    <div>
      <div className="moduleMetricRow">
        <div><span>Mode</span><strong>{data.controlMode}</strong></div>
        <div><span>Compensator</span><strong>{data.compensatorType}</strong></div>
        <div><span>Target fc</span><strong>{formatHz(data.targetCrossoverHz)}</strong></div>
      </div>
      <div className="detailTwoCol">
        <section>
          <h4>Parameters</h4>
          <ul className="compactList">{(data.parameters || []).map((item: AnyRecord) => <li key={item.name}>{item.name}: {item.value} {item.unit}</li>)}</ul>
        </section>
        <section>
          <h4>Validation</h4>
          <ul className="compactList">{(data.validation || []).map((item: AnyRecord) => <li key={item.check}>{item.check}: {String(item.result ?? "-")}</li>)}</ul>
        </section>
      </div>
    </div>
  );
}

function PcbAutomationDetail({ data }: { data: AnyRecord }) {
  const steps = data.automationSteps || [];
  if (!steps.length) return <div className="empty">Run PCB to populate the fake KiCad/JLCPCB automation pipeline.</div>;
  return (
    <div className="pcbStepGrid">
      {steps.map((step: AnyRecord) => (
        <article className="pcbStepCard" key={step.step}>
          <span>{step.status}</span>
          <strong>{step.step}</strong>
          <p>{step.output}</p>
          <small>{step.notice}</small>
        </article>
      ))}
    </div>
  );
}

function GenericModuleDetail({ stage, plan }: { stage: WorkflowStep; plan: WorkflowPlan }) {
  const profile = demoProfileForPlan(plan);
  const profileResult = profile.moduleResults[stage.id];
  const linkedModules = [...plan.modules.required, ...plan.modules.recommended, ...plan.modules.optional].filter((moduleItem) =>
    stage.moduleIds.includes(moduleItem.id),
  );
  if (profileResult) {
    return (
      <div className="detailTwoCol">
        <section>
          <h4>{profileResult.title}</h4>
          <p className="detailText">{stage.description}</p>
          <ul className="compactList">
            {profileResult.outputs.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </section>
        <section>
          <h4>Generated Fake Artifacts</h4>
          <ul className="compactList">
            {profileResult.artifacts.map((item) => <li key={item}>{item}</li>)}
          </ul>
          <p className="detailText">{profileResult.status}</p>
        </section>
      </div>
    );
  }
  return (
    <div className="detailTwoCol">
      <section>
        <h4>Module Intent</h4>
        <p className="detailText">{stage.description}</p>
        <p className="detailText">This step is selected by the workflow planner for the current domain pack.</p>
      </section>
      <section>
        <h4>Selected Modules</h4>
        <ul className="compactList">
          {linkedModules.length ? linkedModules.map((item) => <li key={item.id}>{item.name}: {item.reason}</li>) : <li>Planning placeholder. No executable module is connected yet.</li>}
        </ul>
      </section>
    </div>
  );
}

function SimulationDetail({ data }: { data: AnyRecord }) {
  if (!data.available) return <div className="empty">Run Simulation to generate synthetic waveform metrics.</div>;
  return (
    <div className="moduleMetricRow">
      <div><span>Ripple</span><strong>{data.metrics?.vout_ripple_mv_pp ?? "-"} mVpp</strong></div>
      <div><span>Transient</span><strong>{data.metrics?.vout_transient_deviation_mv ?? "-"} mV</strong></div>
      <div><span>Inductor Peak</span><strong>{data.metrics?.inductor_peak_a ?? "-"} A</strong></div>
      <div><span>Source</span><strong>Synthetic</strong></div>
    </div>
  );
}

function OutputList({ items }: { items: AnyRecord[] }) {
  if (!items?.length) return <div className="empty">Waiting for demo outputs.</div>;
  return (
    <ul className="outputList">
      {items.map((item: AnyRecord) => (
        <li key={`${item.label}-${item.path}`}>
          <strong>{item.label || "Output"}</strong>
          <span>{item.path || "-"}</span>
        </li>
      ))}
    </ul>
  );
}

function TestWorkflowDetail({ data, focusId }: { data: AnyRecord; focusId?: string }) {
  const cards = data.cards || [];
  const activeCard = cards.find((card: AnyRecord) => card.id === focusId) || cards[0];
  if (!data.available) return <div className="empty">Run the demo to generate fake post-prototype Test results.</div>;

  const codes = data.codes || {};
  const tuning = data.tuning || {};
  const logged = data.data || {};
  const report = data.report || {};
  const renderFocusedDetail = () => {
    switch (activeCard?.id) {
      case "embedded_coding_download":
        return (
          <div className="detailTwoCol">
            <section>
              <h4>Flash Log</h4>
              <ul className="compactList">
                {(codes.flashLog || []).map((item: AnyRecord) => (
                  <li key={item.step}>{item.step}: {item.detail}</li>
                ))}
              </ul>
            </section>
            <section>
              <h4>Generated Outputs</h4>
              <OutputList items={codes.outputs || []} />
            </section>
          </div>
        );
      case "closed_loop_tuning":
        return (
          <div className="detailTwoCol">
            <section>
              <h4>Tuning Sweep</h4>
              <ul className="compactList">
                {(tuning.parameterSweep || []).map((item: AnyRecord) => (
                  <li key={item.iteration}>
                    Iteration {item.iteration}: settling {item.settlingMs} ms, overshoot {item.overshootPercent}%, phase margin {item.phaseMarginDeg} deg
                  </li>
                ))}
              </ul>
            </section>
            <section>
              <h4>Validation</h4>
              <ul className="compactList">
                {(tuning.validation || []).map((item: AnyRecord) => (
                  <li key={item.check}>{item.check}: {item.result} ({item.status})</li>
                ))}
              </ul>
            </section>
          </div>
        );
      case "efficiency_logging":
        return (
          <div>
            <div className="moduleMetricRow">
              {(logged.summaryCards || []).map((card: AnyRecord) => (
                <div key={card.label}><span>{card.label}</span><strong>{card.value}</strong></div>
              ))}
            </div>
            <div className="bomTableWrap">
              <table className="bomTable">
                <thead>
                  <tr>
                    <th>Vin</th>
                    <th>Load</th>
                    <th>Vout</th>
                    <th>Efficiency</th>
                    <th>Hot Spot</th>
                    <th>Ripple</th>
                  </tr>
                </thead>
                <tbody>
                  {(logged.efficiencyPoints || []).map((point: AnyRecord) => (
                    <tr key={`${point.vinV}-${point.loadA}`}>
                      <td>{point.vinV} V</td>
                      <td>{point.loadA} A</td>
                      <td>{point.voutV} V</td>
                      <td>{point.efficiencyPercent}%</td>
                      <td>{point.hotSpotC} C</td>
                      <td>{point.rippleMvpp} mVpp</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        );
      case "test_report":
        return (
          <div className="detailTwoCol">
            <section>
              <h4>Report Sections</h4>
              <ul className="compactList">
                {(report.sections || []).map((item: AnyRecord) => (
                  <li key={item.title}>{item.title}: {item.status}</li>
                ))}
              </ul>
            </section>
            <section>
              <h4>Revision Actions</h4>
              <ul className="compactList">
                {(report.revisionActions || []).map((item: string) => <li key={item}>{item}</li>)}
              </ul>
            </section>
          </div>
        );
      default:
        return <div className="empty">Select a Test module to inspect its fake result.</div>;
    }
  };

  return (
    <div className="testWorkflowDetail">
      <div className="pcbStepGrid">
        {cards.map((card: AnyRecord) => (
          <article className={`pcbStepCard ${card.id === activeCard?.id ? "selected" : ""}`} key={card.id}>
            <span>{card.status}</span>
            <strong>{card.title}</strong>
            <p>{card.summary}</p>
            <small>{card.outputPreview}</small>
          </article>
        ))}
      </div>
      <div className="testFocusPanel">
        <div className="testFocusHeader">
          <div>
            <span>{activeCard?.label}</span>
            <h4>{activeCard?.title}</h4>
          </div>
          <small>{activeCard?.sourceType} / {activeCard?.realCapabilityStatus}</small>
        </div>
        {renderFocusedDetail()}
      </div>
    </div>
  );
}

function ModuleDetailPanel({ stage, state, plan }: { stage: WorkflowStep & AnyRecord; state: AnyRecord; plan: WorkflowPlan }) {
  const testPayload = state.testWorkflow || {};
  const profile = demoProfileForPlan(plan);
  const detailMap: Record<string, { title: string; payload: AnyRecord; body: React.ReactNode }> = {
    specifications: { title: "Execution Plan", payload: state.executionPlan || {}, body: <ExecutionPlanDetail data={state.executionPlan || {}} /> },
    parts: { title: "BOM Search Results", payload: state.partsCatalog || {}, body: <PartsCatalogDetail data={state.partsCatalog || {}} /> },
    analysis: { title: "Loss + Thermal Analysis", payload: state.analysisSummary || {}, body: <AnalysisDetail data={state.analysisSummary || {}} /> },
    simulation: { title: "Simulation Evidence", payload: state.waveforms || {}, body: <SimulationDetail data={state.waveforms || {}} /> },
    control: { title: "Control Plan", payload: state.controlPlan || {}, body: <ControlPlanDetail data={state.controlPlan || {}} /> },
    pcb: { title: "PCB Automation Plan", payload: state.pcbAutomationPlan || {}, body: <PcbAutomationDetail data={state.pcbAutomationPlan || {}} /> },
    embedded_coding_download: { title: "Post-Prototype Test Workflow", payload: testPayload, body: <TestWorkflowDetail data={testPayload} focusId="embedded_coding_download" /> },
    closed_loop_tuning: { title: "Post-Prototype Test Workflow", payload: testPayload, body: <TestWorkflowDetail data={testPayload} focusId="closed_loop_tuning" /> },
    efficiency_logging: { title: "Post-Prototype Test Workflow", payload: testPayload, body: <TestWorkflowDetail data={testPayload} focusId="efficiency_logging" /> },
    test_report: { title: "Post-Prototype Test Workflow", payload: testPayload, body: <TestWorkflowDetail data={testPayload} focusId="test_report" /> },
  };
  const detail = detailMap[stage.id] || {
    title: `${profile.projectName} Module`,
    payload: { sourceType: profile.id, realCapabilityStatus: "planning_placeholder", notice: profile.fakeNotice },
    body: <GenericModuleDetail stage={stage} plan={plan} />,
  };
  return (
    <section className="moduleDetailPanel">
      <div className="moduleDetailHeader">
        <div>
          <span>{stage.title}</span>
          <h3>{detail.title}</h3>
        </div>
        <CapabilityNotice payload={detail.payload} />
      </div>
      {detail.body}
    </section>
  );
}

function StageTimeline({ state, plan }: { state: AnyRecord; plan: WorkflowPlan }) {
  const stages = combinedStagePayloads(state);
  const [activeStageId, setActiveStageId] = React.useState<string | null>(null);
  React.useEffect(() => {
    setActiveStageId(null);
  }, [plan.requestText]);
  const plannedSections = plan.workflowSections.map((section) => ({
    ...section,
    steps: section.steps.map((stepItem, index) => ({
      ...stepItem,
      index: index + 1,
      status: sourceStatus(stages, stepItem.sourceStageIds),
    })),
  }));
  const allRoadmapStages = plannedSections.flatMap((section) => section.steps);
  const hasRealStatus = allRoadmapStages.some((stage) => ["running", "complete", "partial", "blocked", "error", "failed"].includes(stage.status));
  const completedCount = allRoadmapStages.filter((stage) => stage.status === "complete").length;
  const activeStage = allRoadmapStages.find((stage) => stage.id === activeStageId) || allRoadmapStages[0];

  const renderStageCard = (stage: AnyRecord) => (
    <div
      className={`roadmapCard state-${String(stage.status || "waiting").toLowerCase().replace(/_/g, "-")} ${stage.id === activeStageId ? "selected" : ""}`}
      key={stage.id}
      role="button"
      tabIndex={0}
      onClick={() => setActiveStageId(stage.id)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          setActiveStageId(stage.id);
        }
      }}
    >
      <div className="roadmapCardTop">
        <span className="roadmapStepNumber">{stage.index}</span>
        <span className="roadmapStatus" aria-label={`Status: ${stage.status}`}>
          <span />
          {statusDisplay(stage.status) && <em>{statusDisplay(stage.status)}</em>}
        </span>
      </div>
      <div className="roadmapCardBody">
        <span className="roadmapIcon">
          <RoadmapIcon name={stage.icon} />
        </span>
        <h3>{stage.title}</h3>
      </div>
    </div>
  );

  return (
    <section className="panel systemMapPanel">
      <div className="panelHeader systemMapHeader">
        <div>
          <h2>Workflow Modules</h2>
          <p>{plan.selectedPacks.map((pack) => pack.uiLabels.workflowSubtitle).join(" ")}</p>
        </div>
        <div className="roadmapSummary">
          <span>{completedCount} / {allRoadmapStages.length} completed</span>
          <strong>{hasRealStatus ? "Workflow Status" : "Planner Preview"}</strong>
        </div>
      </div>
      <div className="systemMapGroups">
        {plannedSections.map((section) => (
          <div className="roadmapSection" key={`${section.label}-${section.contextLabel}`}>
            <div className="roadmapSectionHeader">
              <span>{section.label}</span>
              <strong>{section.contextLabel}</strong>
            </div>
            <div className="roadmapTrack" style={{ "--step-count": section.steps.length } as React.CSSProperties}>
              {section.steps.map(renderStageCard)}
            </div>
          </div>
        ))}
      </div>
      {activeStage && <ModuleDetailPanel stage={activeStage} state={state} plan={plan} />}
    </section>
  );
}

const SPEC_FIELDS = [
  { key: "input_voltage_min_v", label: "Vin min", unit: "V", step: "0.1" },
  { key: "input_voltage_nominal_v", label: "Vin nom", unit: "V", step: "0.1" },
  { key: "input_voltage_max_v", label: "Vin max", unit: "V", step: "0.1" },
  { key: "output_voltage_v", label: "Vout", unit: "V", step: "0.1" },
  { key: "output_current_a", label: "Iout", unit: "A", step: "0.1" },
  { key: "output_ripple_mv_pp", label: "Ripple", unit: "mVpp", step: "1" },
  { key: "transient_step_a", label: "Load step", unit: "A", step: "0.1" },
  { key: "transient_deviation_mv", label: "Transient", unit: "mV", step: "1" },
  { key: "target_efficiency_percent", label: "Eff min", unit: "%", step: "0.1" },
  { key: "ambient_temp_c", label: "Ambient", unit: "C", step: "1" },
  { key: "max_total_loss_w", label: "Loss max", unit: "W", step: "0.01" }
];

const DEFAULT_DEMO_SPEC: AnyRecord = {
  name: "AutoEE 15W USB-C Buck Charger Demo",
  input_voltage_min_v: 9.0,
  input_voltage_nominal_v: 12.0,
  input_voltage_max_v: 36.0,
  output_voltage_v: 5.0,
  output_current_a: 3.0,
  output_ripple_mv_pp: 50.0,
  transient_step_a: 2.7,
  transient_deviation_mv: 250.0,
  target_efficiency_percent: 90.0,
  ambient_temp_c: 60.0,
  max_total_loss_w: 1.7
};

function toEditableSpec(spec: AnyRecord): AnyRecord {
  const source = spec || {};
  const draft: AnyRecord = {
    name: String(source.name || DEFAULT_DEMO_SPEC.name)
  };
  SPEC_FIELDS.forEach((field) => {
    const value = source[field.key];
    draft[field.key] = value === undefined || value === null || value === "" ? String(DEFAULT_DEMO_SPEC[field.key]) : String(value);
  });
  return draft;
}

function decimalPlaces(step: string): number {
  const text = String(step || "1");
  const dot = text.indexOf(".");
  return dot >= 0 ? text.length - dot - 1 : 0;
}

function SpecNumberInput({
  field,
  value,
  onChange
}: {
  field: AnyRecord;
  value: string;
  onChange: (value: string) => void;
}) {
  const places = decimalPlaces(field.step);
  const step = Number(field.step || 1);
  const adjust = (direction: number) => {
    const current = Number(value);
    const base = Number.isFinite(current) ? current : Number(DEFAULT_DEMO_SPEC[field.key] || 0);
    onChange((base + direction * step).toFixed(places));
  };
  return (
    <div className="unitInput">
      <button type="button" className="stepButton" onClick={() => adjust(-1)} aria-label={`Decrease ${field.label}`}>
        -
      </button>
      <input
        type="text"
        inputMode="decimal"
        value={value ?? ""}
        placeholder={String(DEFAULT_DEMO_SPEC[field.key] ?? "")}
        onChange={(event) => onChange(event.target.value)}
      />
      <button type="button" className="stepButton" onClick={() => adjust(1)} aria-label={`Increase ${field.label}`}>
        +
      </button>
      <em>{field.unit}</em>
    </div>
  );
}

function ArtifactPackage({ state, actions, plan, showSpecEditor = false }: { state: AnyRecord; actions: AnyRecord; plan: WorkflowPlan; showSpecEditor?: boolean }) {
  const stages = combinedStagePayloads(state);
  const spec = state.spec || state.rawState?.spec || {};
  const profile = demoProfileForPlan(plan);
  const canEditPowerSpec = showSpecEditor && plan.classification.primaryDomain === "power_electronics";
  const [draft, setDraft] = React.useState<AnyRecord>(() => toEditableSpec(spec));
  const [error, setError] = React.useState("");
  const [dirty, setDirty] = React.useState(false);
  React.useEffect(() => {
    if (!dirty) {
      setDraft(toEditableSpec(spec));
      setError("");
    }
  }, [JSON.stringify(spec), dirty]);
  const artifactItems = plan.artifacts.map((artifactItem) => ({
    ...artifactItem,
    status: sourceStatus(stages, artifactItem.sourceStageIds),
  }));
  const ready = artifactItems.length > 0 && artifactItems.every((item) => item.status === "complete");
  const updateDraft = (key: string, value: string) => {
    setDirty(true);
    setDraft((current: AnyRecord) => ({ ...current, [key]: value }));
  };
  const apply = async () => {
    setError("");
    const nextSpec: AnyRecord = { name: String(draft.name || "").trim() };
    SPEC_FIELDS.forEach((field) => {
      nextSpec[field.key] = Number(draft[field.key]);
    });
    if (!nextSpec.name) {
      setError("Project name is required.");
      return;
    }
    if (SPEC_FIELDS.some((field) => !Number.isFinite(nextSpec[field.key]))) {
      setError("Every numeric spec needs a valid number.");
      return;
    }
    try {
      await actions.applySpec(nextSpec);
      setDirty(false);
    } catch (exc: any) {
      setError(exc.message || "Failed to apply specs.");
    }
  };
  return (
    <section className="panel packagePanel">
      <div className="panelHeader">
        <div>
          <h2>{showSpecEditor ? "Artifacts" : ready ? "Generated Hardware Package Ready" : plan.selectedPacks[0]?.uiLabels.packageTitle || "Generated Hardware Package"}</h2>
          <p>{showSpecEditor ? profile.packageSummary : "Artifacts are selected by the active domain pack. Placeholder packs show intended deliverables only."}</p>
        </div>
      </div>
      {canEditPowerSpec && (
        <details className="specEditorDisclosure">
          <summary>Edit specs</summary>
          <div className="specEditor">
            <label className="specName">
              <span>Design Brief</span>
              <input value={draft.name} onChange={(event) => updateDraft("name", event.target.value)} />
            </label>
            <div className="specFormGrid">
              {SPEC_FIELDS.map((field) => (
                <label className="specInputRow" key={field.key}>
                  <span>{field.label}</span>
                  <SpecNumberInput field={field} value={String(draft[field.key] ?? "")} onChange={(value) => updateDraft(field.key, value)} />
                </label>
              ))}
            </div>
            {error && <div className="formError">{error}</div>}
            <button className="applySpecs" onClick={apply} disabled={state.running}>
              Apply Specs
            </button>
          </div>
        </details>
      )}
      <div className="packageSubhead">Artifact Package</div>
      <div className="packageList">
        {artifactItems.map((artifactItem: ArtifactDefinition & { status: string }) => (
          <div className="packageItem" key={artifactItem.id}>
            <StatusDot status={artifactItem.status} />
            <div>
              <strong>{artifactItem.label}</strong>
              <span>{compactStatusLabel(artifactItem.status)}</span>
              <small>{artifactItem.description}</small>
            </div>
          </div>
        ))}
        {!artifactItems.length && (
          <div className="empty">Select a project request to preview generated artifacts.</div>
        )}
      </div>
    </section>
  );
}

function ModuleSelectionPanel({ plan }: { plan: WorkflowPlan }) {
  const groups: Array<[string, CapabilityModule[]]> = [
    ["Required", plan.modules.required],
    ["Recommended", plan.modules.recommended],
    ["Optional", plan.modules.optional],
  ];
  return (
    <section className="panel moduleSelectionPanel">
      <div className="panelHeader">
        <div>
          <h2>Engineering Modules</h2>
          <p>Required, recommended, and optional modules for this project.</p>
        </div>
      </div>
      <div className="moduleSelectionGrid">
        {groups.map(([label, modules]) => (
          <section className="moduleGroup" key={label}>
            <h3>{label}</h3>
            <div className="moduleCardList">
              {modules.map((moduleItem) => (
                <article className={`moduleSelectCard ${moduleItem.statusCategory}`} key={moduleItem.id}>
                  <div>
                    <span className="roadmapIcon"><RoadmapIcon name={moduleItem.icon} /></span>
                    <strong>{moduleItem.name}</strong>
                  </div>
                  <p>{moduleItem.reason}</p>
                  <small>{domainName(moduleItem.domain)} / {moduleItem.appearsInWorkflow ? "active workflow" : "supporting"}</small>
                </article>
              ))}
              {!modules.length && <div className="empty">No modules in this group.</div>}
            </div>
          </section>
        ))}
      </div>
    </section>
  );
}

function StatusDot({ status }: { status: string }) {
  return <span className={`statusDot ${String(status || "waiting")}`} />;
}

function compactStatusLabel(status: string): string {
  if (status === "complete") return "Done";
  if (status === "running" || status === "active") return "Active";
  if (status === "partial") return "Partial";
  if (["blocked", "error", "failed"].includes(status)) return "Blocked";
  return "Pending";
}

function DynamicMetricsPanel({ state, plan }: { state: AnyRecord; plan: WorkflowPlan }) {
  return (
    <section className="panel">
      <div className="panelHeader">
        <div>
          <h2>Validation Metrics</h2>
          <p>Domain-specific checks generated from the selected workflow.</p>
        </div>
      </div>
      <div className="energyGrid">
        {plan.metrics.map((metric) => {
          const metricValue = metricFromDefinition(metric, state, plan);
          return (
          <div className={`energyCard tone-${metricValue.tone || "neutral"}`} key={metric.id}>
            <span>{metric.label}</span>
            <strong>{metricValue.display}</strong>
            <p>{metric.description}</p>
          </div>
          );
        })}
      </div>
    </section>
  );
}

function EvidenceRail({ state }: { state: AnyRecord }) {
  const risks = state.riskSummary?.risks || [];
  const missing = state.riskSummary?.missingData || [];
  return (
    <aside className="rightRail">
      <section className="panel">
        <h2>Evidence Badges</h2>
        <div className="badgeList">
          {(state.evidenceBadges || []).map((badge: AnyRecord) => (
            <div className="evidenceBadge" key={`${badge.label}-${badge.sourceType}`}>
              <strong>{badge.label}</strong>
              <span>{badge.sourceType}</span>
              <small>
                {badge.confidence} / {badge.signoffStatus}
              </small>
            </div>
          ))}
        </div>
      </section>
      <section className="panel">
        <h2>Risk Snapshot</h2>
        <div className="riskCounts">
          <div>
            <strong>{risks.length}</strong>
            <span>Known risks</span>
          </div>
          <div>
            <strong>{missing.length}</strong>
            <span>Missing evidence</span>
          </div>
        </div>
        <ul className="compactList">
          {(state.nextActions || []).slice(0, 5).map((action: string) => (
            <li key={action}>{action}</li>
          ))}
        </ul>
      </section>
    </aside>
  );
}

function ProfileModuleSummary({ profile, moduleIds }: { profile: DemoCircuitProfile; moduleIds: string[] }) {
  const modules = moduleIds.map((id) => profile.moduleResults[id]).filter(Boolean);
  return (
    <div className="profileModuleGrid">
      {modules.map((moduleItem) => (
        <article className="profileModuleCard" key={moduleItem.title}>
          <span>{moduleItem.status}</span>
          <h3>{moduleItem.title}</h3>
          <ul className="compactList">
            {moduleItem.outputs.map((item) => <li key={item}>{item}</li>)}
          </ul>
          <small>{moduleItem.artifacts.join(", ")}</small>
        </article>
      ))}
    </div>
  );
}

function ProfileMetricPanel({ profile, metricIds }: { profile: DemoCircuitProfile; metricIds: string[] }) {
  return (
    <div className="moduleMetricRow">
      {metricIds.map((id) => {
        const metric = profile.metrics[id] || { display: "Pending", tone: "neutral" };
        return (
          <div className={`tone-${metric.tone || "neutral"}`} key={id}>
            <span>{id.replace(/_/g, " ")}</span>
            <strong>{metric.display}</strong>
            {metric.target && <small>Target {metric.target}</small>}
          </div>
        );
      })}
    </div>
  );
}

function DomainDetailPanel({ profile, title, summary, metricIds, moduleIds }: { profile: DemoCircuitProfile; title: string; summary: string; metricIds: string[]; moduleIds: string[] }) {
  return (
    <div className="domainDetailPanel">
      <div className="domainDetailHeader">
        <div>
          <span>{profile.circuitName}</span>
          <h3>{title}</h3>
          <p>{summary}</p>
        </div>
        <small>Demo data / Not connected</small>
      </div>
      <ProfileMetricPanel profile={profile} metricIds={metricIds} />
      <ProfileModuleSummary profile={profile} moduleIds={moduleIds} />
    </div>
  );
}

function EngineeringTabs({ state, plan }: { state: AnyRecord; plan: WorkflowPlan }) {
  const profile = demoProfileForPlan(plan);
  const isPower = plan.classification.primaryDomain === "power_electronics";
  const domain = plan.classification.primaryDomain;
  const tabs = isPower
    ? [
        ["waveforms", "Waveforms"],
        ["loss", "Loss/Thermal"],
        ["rationale", "Design Rationale"],
        ["risk", "Risk Summary"],
        ["json", "Developer State"],
      ]
    : domain === "rf_communication" || plan.classification.domains.includes("rf_communication")
      ? [
          ["rf", "Link Budget / RF Plan"],
          ["firmware", "Firmware & Power Budget"],
          ["risk", "Risk Summary"],
          ["json", "Developer State"],
        ]
      : domain === "analog_sensor"
        ? [
            ["signal", "Signal Chain"],
            ["noise", "Noise Budget"],
            ["calibration", "Calibration Plan"],
            ["risk", "Risk Summary"],
            ["json", "Developer State"],
          ]
        : domain === "high_speed_digital"
          ? [
              ["si_pi", "SI / PI"],
              ["stackup", "Stackup & Timing"],
              ["risk", "Risk Summary"],
              ["json", "Developer State"],
            ]
          : [
              ["board", "Board Plan"],
              ["io", "Component / I/O Map"],
              ["assembly", "Assembly Review"],
              ["risk", "Risk Summary"],
              ["json", "Developer State"],
            ];
  const [tab, setTab] = React.useState(tabs[0][0]);
  React.useEffect(() => {
    setTab(tabs[0][0]);
  }, [profile.id]);
  return (
    <section className="engineering panel">
      <div className="tabBar">
        {tabs.map(([id, label]) => (
          <button className={tab === id ? "active" : ""} onClick={() => setTab(id)} key={id}>
            {label}
          </button>
        ))}
      </div>
      {tab === "waveforms" && <WaveformOverview data={state.waveforms} />}
      {tab === "loss" && <LossThermal data={state.lossThermal} />}
      {tab === "rationale" && <DesignRationale data={state.designRationale} />}
      {tab === "rf" && <DomainDetailPanel profile={profile} title="RF Link Budget And Antenna Plan" summary="Wireless range, RF SoC choice, antenna matching, and RF layout constraints for the BLE sensor node." metricIds={["link_margin", "range", "tx_power", "rx_sensitivity", "antenna_risk"]} moduleIds={["rf_requirements", "rf_ic_selection", "link_budget", "antenna_matching", "rf_layout"]} />}
      {tab === "firmware" && <DomainDetailPanel profile={profile} title="Firmware And Coin-Cell Power Budget" summary="Embedded firmware tasks, low-power modes, programming flow, and manufacturing test coverage." metricIds={["battery_life", "sleep_current", "io_usage", "firmware_risk", "bom_cost"]} moduleIds={["mcu_selection", "firmware_architecture", "embedded_power_budget", "manufacturing_test"]} />}
      {tab === "signal" && <DomainDetailPanel profile={profile} title="Analog Signal Chain" summary="Thermocouple input protection, amplifier, cold-junction compensation, reference, ADC, and digital output plan." metricIds={["bandwidth", "resolution", "accuracy"]} moduleIds={["signal_chain", "sensor_selection", "op_amp_adc", "analog_layout"]} />}
      {tab === "noise" && <DomainDetailPanel profile={profile} title="Noise Budget And Accuracy Estimate" summary="Input-referred noise, effective temperature resolution, bandwidth, and drift risk for the measurement front-end." metricIds={["noise", "bandwidth", "resolution", "accuracy", "drift_risk"]} moduleIds={["noise_budget"]} />}
      {tab === "calibration" && <DomainDetailPanel profile={profile} title="Calibration Plan" summary="Two-point calibration, cold-junction trim, open-sensor fault test, and production coefficient storage." metricIds={["accuracy", "drift_risk"]} moduleIds={["calibration"]} />}
      {tab === "si_pi" && <DomainDetailPanel profile={profile} title="Signal And Power Integrity Plan" summary="USB 3.0, DDR, power tree, decoupling, and early SI/PI risk estimates for the FPGA board." metricIds={["eye_margin", "pdn_risk", "interface_speed", "timing_risk"]} moduleIds={["processor_fpga", "memory_interface", "signal_integrity", "power_integrity"]} />}
      {tab === "stackup" && <DomainDetailPanel profile={profile} title="Stackup And Timing Constraints" summary="Layer count, controlled impedance rules, reference planes, return vias, and timing constraint notes." metricIds={["layer_count", "interface_speed", "timing_risk"]} moduleIds={["stackup", "timing_constraints"]} />}
      {tab === "board" && <DomainDetailPanel profile={profile} title="General Controller Board Plan" summary="Board requirements, MCU/regulator structure, connector map, LEDs, programming header, and test-point strategy." metricIds={["bom_cost", "layer_count", "connector_count"]} moduleIds={["requirements", "component_inventory", "layout_constraints"]} />}
      {tab === "io" && <DomainDetailPanel profile={profile} title="Component And I/O Map" summary="Connector groups, GPIO allocation, LED/button assignments, protection passives, and programming access." metricIds={["connector_count", "bom_cost"]} moduleIds={["component_inventory", "connector_io"]} />}
      {tab === "assembly" && <DomainDetailPanel profile={profile} title="Assembly Review" summary="Assembly risk, connector placement, polarity checks, test access, and production notes." metricIds={["assembly_risk", "drc_risk", "layer_count"]} moduleIds={["assembly_review", "layout_constraints"]} />}
      {tab === "risk" && <RiskSummary data={state.riskSummary} />}
      {tab === "json" && <pre className="jsonBlock">{JSON.stringify(state.rawState, null, 2)}</pre>}
    </section>
  );
}

function scalePoint(value: number, min: number, max: number, low: number, high: number): number {
  if (max <= min) return (low + high) / 2;
  return low + ((value - min) / (max - min)) * (high - low);
}

function buildPath(xs: number[], ys: number[], width: number, height: number, pad: number, ymin?: number, ymax?: number): string {
  if (!xs.length || !ys.length) return "";
  const xMin = Math.min(...xs);
  const xMax = Math.max(...xs);
  const yMin = ymin ?? Math.min(...ys);
  const yMax = ymax ?? Math.max(...ys);
  return xs
    .map((x, index) => {
      const px = scalePoint(x, xMin, xMax, pad, width - pad);
      const py = scalePoint(ys[index], yMin, yMax, height - pad, pad);
      return `${index === 0 ? "M" : "L"} ${px.toFixed(2)} ${py.toFixed(2)}`;
    })
    .join(" ");
}

function buildLogXPath(xs: number[], ys: number[], width: number, height: number, pad: number, ymin?: number, ymax?: number): string {
  if (!xs.length || !ys.length) return "";
  const safeXs = xs.map((value) => Math.max(Number(value), 1e-9));
  const logXs = safeXs.map((value) => Math.log10(value));
  const xMin = Math.min(...logXs);
  const xMax = Math.max(...logXs);
  const yMin = ymin ?? Math.min(...ys);
  const yMax = ymax ?? Math.max(...ys);
  return logXs
    .map((x, index) => {
      const px = scalePoint(x, xMin, xMax, pad, width - pad);
      const py = scalePoint(ys[index], yMin, yMax, height - pad, pad);
      return `${index === 0 ? "M" : "L"} ${px.toFixed(2)} ${py.toFixed(2)}`;
    })
    .join(" ");
}

function MiniLineChart({
  title,
  x,
  y,
  color,
  ymin,
  ymax,
  annotations = []
}: {
  title: string;
  x: number[];
  y: number[];
  color: string;
  ymin?: number;
  ymax?: number;
  annotations?: AnyRecord[];
}) {
  const width = 520;
  const height = 150;
  const pad = 26;
  const path = buildPath(x, y, width, height, pad, ymin, ymax);
  return (
    <div className="chartCard">
      <div className="chartTitle">{title}</div>
      <svg viewBox={`0 0 ${width} ${height}`} className="lineChart">
        <rect x={pad} y={pad} width={width - pad * 2} height={height - pad * 2} rx="8" />
        {annotations.map((ann) => (
          <line key={ann.label} x1={pad} x2={width - pad} y1={scalePoint(ann.value, ymin ?? Math.min(...y), ymax ?? Math.max(...y), height - pad, pad)} y2={scalePoint(ann.value, ymin ?? Math.min(...y), ymax ?? Math.max(...y), height - pad, pad)} className={ann.className || "guide"} />
        ))}
        <path d={path} stroke={color} />
      </svg>
    </div>
  );
}

function WaveformOverview({ data }: { data: AnyRecord }) {
  const series = data?.series || {};
  const x = (series.time_us || []).map(Number);
  if (!data?.available || !x.length) {
    return <div className="emptyBig">Run the demo to generate synthetic buck waveforms.</div>;
  }
  const limits = data.limits || {};
  const vout = (series.vout_v || []).map(Number);
  const il = (series.il_a || []).map(Number);
  const sw = (series.switch_v || []).map(Number);
  const load = (series.load_current_a || []).map(Number);
  return (
    <div>
      <div className="sourceBanner">{data.sourceBadge}</div>
      <div className="waveGrid">
        <MiniLineChart
          title="Vout vs limits: 5V rail stability"
          x={x}
          y={vout}
          color="#00a383"
          ymin={Math.min(limits.transient_lower_v ?? 4.75, ...vout)}
          ymax={Math.max(limits.transient_upper_v ?? 5.25, ...vout)}
          annotations={[
            { label: "nominal", value: limits.nominal_v ?? 5, className: "guide nominal" },
            { label: "rippleUpper", value: limits.ripple_upper_v ?? 5.025, className: "guide good" },
            { label: "rippleLower", value: limits.ripple_lower_v ?? 4.975, className: "guide good" }
          ]}
        />
        <MiniLineChart title="Inductor current IL: peak and valley safety" x={x} y={il} color="#4f7cff" ymin={Math.min(0, ...il)} ymax={Math.max(...il) * 1.15} />
        <MiniLineChart title="Switch node SW: PWM duty and frequency" x={x} y={sw} color="#f2a93b" ymin={0} ymax={Math.max(...sw) * 1.15} />
        <MiniLineChart title="Load step: why transient happens" x={x} y={load} color="#9b5cf6" ymin={0} ymax={Math.max(...load) * 1.2} />
      </div>
      <div className="metricRow">
        <MetricChip label="Ripple" value={`${data.metrics?.vout_ripple_mv_pp ?? "-"} mVpp`} />
        <MetricChip label="Transient" value={`${data.metrics?.vout_transient_deviation_mv ?? "-"} mV`} />
        <MetricChip label="IL peak" value={`${data.metrics?.inductor_peak_a ?? "-"} A`} />
        <MetricChip label="Duty" value={`${data.metrics?.duty_nominal ?? "-"}`} />
      </div>
      <ControlBodePlot data={data.controlBode} />
    </div>
  );
}

function formatHz(value: any): string {
  const number = Number(value);
  if (!Number.isFinite(number)) return "-";
  if (Math.abs(number) >= 1_000_000) return `${(number / 1_000_000).toFixed(2)} MHz`;
  if (Math.abs(number) >= 1_000) return `${(number / 1_000).toFixed(2)} kHz`;
  return `${number.toFixed(0)} Hz`;
}

function formatNum(value: any, suffix = "", digits = 1): string {
  const number = Number(value);
  if (!Number.isFinite(number)) return "-";
  return `${number.toFixed(digits)}${suffix}`;
}

function ControlBodePlot({ data }: { data: AnyRecord }) {
  const series = data?.series || {};
  const freq = (series.freq_hz || []).map(Number);
  const mag = (series.mag_db || []).map(Number);
  const phase = (series.phase_deg || []).map(Number);
  const width = 760;
  const height = 360;
  const pad = 48;
  if (!data?.available || !freq.length || !mag.length || !phase.length) {
    return (
      <div className="controlBode emptyBode">
        <div>
          <h3>Closed-loop Bode appears after Design Control</h3>
          <p>Run through Design Control to show the control loop has been designed, with crossover and phase margin.</p>
        </div>
      </div>
    );
  }
  const magMin = Math.floor((Math.min(...mag, -40) - 5) / 10) * 10;
  const magMax = Math.ceil((Math.max(...mag, 40) + 5) / 10) * 10;
  const phaseMin = Math.floor((Math.min(...phase, -220) - 10) / 30) * 30;
  const phaseMax = Math.ceil((Math.max(...phase, 20) + 10) / 30) * 30;
  const crossover = data.metrics?.crossover_hz;
  const phaseMargin = data.metrics?.phase_margin_deg;
  const xLogMin = Math.log10(Math.max(Math.min(...freq), 1e-9));
  const xLogMax = Math.log10(Math.max(...freq));
  const crossoverX = Number.isFinite(Number(crossover)) ? scalePoint(Math.log10(Math.max(Number(crossover), 1e-9)), xLogMin, xLogMax, pad, width - pad) : null;
  return (
    <div className="controlBode">
      <div className="bodeHeader">
        <div>
          <span className="eyebrow">After Design Control</span>
          <h3>Closed-loop Bode: control stability</h3>
          <p>{data.summary}</p>
        </div>
        <div className="bodeMetrics">
          <MetricChip label="Crossover" value={formatHz(crossover)} />
          <MetricChip label="Phase margin" value={formatNum(phaseMargin, " deg", 1)} />
        </div>
      </div>
      <div className="sourceBanner compact">{data.sourceBadge}: demo-backed, not signoff</div>
      <svg viewBox={`0 0 ${width} ${height}`} className="bodeChart">
        <rect x={pad} y={pad} width={width - pad * 2} height={(height - pad * 2) / 2 - 8} rx="10" />
        <rect x={pad} y={height / 2 + 8} width={width - pad * 2} height={(height - pad * 2) / 2 - 8} rx="10" />
        <text x={pad} y={26} className="axisLabel">Magnitude (dB)</text>
        <text x={pad} y={height / 2 - 2} className="axisLabel">Phase (deg)</text>
        <line x1={pad} x2={width - pad} y1={scalePoint(0, magMin, magMax, height / 2 - 20, pad)} y2={scalePoint(0, magMin, magMax, height / 2 - 20, pad)} className="guide nominal" />
        <line x1={pad} x2={width - pad} y1={scalePoint(-180, phaseMin, phaseMax, height - pad, height / 2 + 20)} y2={scalePoint(-180, phaseMin, phaseMax, height - pad, height / 2 + 20)} className="guide warn" />
        {crossoverX !== null && (
          <line x1={crossoverX} x2={crossoverX} y1={pad} y2={height - pad} className="guide good" />
        )}
        <path d={buildLogXPath(freq, mag, width, height / 2, pad, magMin, magMax)} stroke="#00a383" />
        <g transform={`translate(0 ${height / 2})`}>
          <path d={buildLogXPath(freq, phase, width, height / 2, pad, phaseMin, phaseMax)} stroke="#4f7cff" />
        </g>
      </svg>
      <div className="legend outside">
        <span><i style={{ background: "#00a383" }} />Loop gain</span>
        <span><i style={{ background: "#4f7cff" }} />Phase</span>
        <span><i className="dash" />0 dB / -180 deg guides</span>
      </div>
    </div>
  );
}

function MetricChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="metricChip">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function EfficiencyChart({ sweep }: { sweep: AnyRecord }) {
  const currents: number[] = (sweep.currentsA || []).map(Number);
  const width = 640;
  const height = 280;
  const pad = 42;
  const curves = sweep.efficiency || [];
  const allY = curves.flatMap((curve: AnyRecord) => (curve.values || []).map(Number));
  const yMin = Math.max(70, Math.floor((Math.min(...allY, 90) - 2) / 5) * 5);
  const yMax = 100;
  return (
    <div className="chartCard large">
      <div className="chartTitle">Efficiency vs output current</div>
      <svg viewBox={`0 0 ${width} ${height}`} className="lineChart">
        <rect x={pad} y={pad} width={width - pad * 2} height={height - pad * 2} rx="10" />
        <text x={pad} y={24} className="axisLabel">
          Higher is better. Curves show Vin sweep.
        </text>
        <line x1={pad} x2={width - pad} y1={scalePoint(sweep.efficiencyTarget ?? 90, yMin, yMax, height - pad, pad)} y2={scalePoint(sweep.efficiencyTarget ?? 90, yMin, yMax, height - pad, pad)} className="guide good" />
        {curves.map((curve: AnyRecord, index: number) => (
          <path key={curve.label} d={buildPath(currents, curve.values.map(Number), width, height, pad, yMin, yMax)} stroke={["#00a383", "#2f80ed", "#f2a93b"][index % 3]} />
        ))}
      </svg>
      <div className="legend outside">
        {curves.map((curve: AnyRecord, index: number) => (
          <span key={curve.label}>
            <i style={{ background: ["#00a383", "#2f80ed", "#f2a93b"][index % 3] }} />
            {curve.label}
          </span>
        ))}
        <span>
          <i className="dash" />
          Efficiency target
        </span>
      </div>
    </div>
  );
}

function LossStackChart({ sweep }: { sweep: AnyRecord }) {
  const currents: number[] = (sweep.currentsA || []).map(Number);
  const width = 640;
  const height = 280;
  const pad = 42;
  const groups = sweep.lossGroups || [];
  const total: number[] = (sweep.totalLossW || []).map(Number);
  const yMax = Math.max(...total, sweep.lossTargetW ?? 1, 0.1) * 1.22;
  let cumulative = new Array(currents.length).fill(0);
  return (
    <div className="chartCard large">
      <div className="chartTitle">Loss vs output current</div>
      <svg viewBox={`0 0 ${width} ${height}`} className="lineChart lossChart">
        <rect x={pad} y={pad} width={width - pad * 2} height={height - pad * 2} rx="10" />
        <text x={pad} y={24} className="axisLabel">
          Filled area is watts lost as heat at nominal Vin.
        </text>
        <line x1={pad} x2={width - pad} y1={scalePoint(sweep.lossTargetW ?? 1.7, 0, yMax, height - pad, pad)} y2={scalePoint(sweep.lossTargetW ?? 1.7, 0, yMax, height - pad, pad)} className="guide warn" />
        {groups.map((group: AnyRecord) => {
          const bottom = cumulative.slice();
          const top = group.values.map((value: number, index: number) => Number(value) + bottom[index]);
          cumulative = top;
          const topPath = currents
            .map((x, index) => `${index === 0 ? "M" : "L"} ${scalePoint(x, currents[0], currents[currents.length - 1], pad, width - pad).toFixed(2)} ${scalePoint(top[index], 0, yMax, height - pad, pad).toFixed(2)}`)
            .join(" ");
          const bottomPath = currents
            .slice()
            .reverse()
            .map((x, revIndex) => {
              const index = currents.length - 1 - revIndex;
              return `L ${scalePoint(x, currents[0], currents[currents.length - 1], pad, width - pad).toFixed(2)} ${scalePoint(bottom[index], 0, yMax, height - pad, pad).toFixed(2)}`;
            })
            .join(" ");
          return <path key={group.group} className="area" fill={GROUP_COLORS[group.group] || "#8a94a6"} d={`${topPath} ${bottomPath} Z`} />;
        })}
        <path d={buildPath(currents, total, width, height, pad, 0, yMax)} stroke="#1f2937" />
      </svg>
      <div className="legend outside">
        {groups.map((group: AnyRecord) => (
          <span key={group.group}>
            <i style={{ background: GROUP_COLORS[group.group] || "#8a94a6" }} />
            {group.group}
          </span>
        ))}
        <span>
          <i className="dash warnDash" />
          Loss target
        </span>
      </div>
    </div>
  );
}

function PieChart({ pie }: { pie: AnyRecord }) {
  const items = pie.items || [];
  const total = items.reduce((sum: number, item: AnyRecord) => sum + Number(item.value || 0), 0);
  let angle = -90;
  const radius = 68;
  const center = 84;
  function arcPath(start: number, end: number): string {
    const startRad = (Math.PI / 180) * start;
    const endRad = (Math.PI / 180) * end;
    const x1 = center + radius * Math.cos(startRad);
    const y1 = center + radius * Math.sin(startRad);
    const x2 = center + radius * Math.cos(endRad);
    const y2 = center + radius * Math.sin(endRad);
    const large = end - start > 180 ? 1 : 0;
    return `M ${center} ${center} L ${x1} ${y1} A ${radius} ${radius} 0 ${large} 1 ${x2} ${y2} Z`;
  }
  return (
    <div className="pieCard">
      <h3>{pie.title}</h3>
      <p>{pie.subtitle}</p>
      <div className="pieLayout">
        <svg viewBox="0 0 168 168" className="pieSvg">
          {items.map((item: AnyRecord) => {
            const start = angle;
            const span = total > 0 ? (Number(item.value) / total) * 360 : 0;
            angle += span;
            return <path key={item.label} d={arcPath(start, angle)} fill={GROUP_COLORS[item.label] || "#8a94a6"} />;
          })}
        </svg>
        <div className="pieLegend">
          {items.map((item: AnyRecord) => (
            <div key={item.label}>
              <i style={{ background: GROUP_COLORS[item.label] || "#8a94a6" }} />
              <span>{item.label}</span>
              <strong>{item.display}</strong>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function LossThermal({ data }: { data: AnyRecord }) {
  if (!data?.available) {
    return <div className="emptyBig">Run Loss + Thermal to see efficiency curves, loss distribution, and temperature cards.</div>;
  }
  return (
    <div className="lossThermal">
      <div className="sourceBanner">{data.sourceBadge}</div>
      <div className="lossGrid">
        <EfficiencyChart sweep={data.sweep || {}} />
        <LossStackChart sweep={data.sweep || {}} />
      </div>
      <div className="pieGrid">
        {(data.pies || []).map((pie: AnyRecord) => (
          <PieChart pie={pie} key={pie.title} />
        ))}
      </div>
      <div className="thermalGrid">
        {(data.thermal?.componentTempsC || []).slice(0, 4).map((temp: AnyRecord) => (
          <div className={`thermalCard tone-${temp.tone}`} key={temp.key}>
            <span>{temp.label}</span>
            <strong>{temp.display}</strong>
          </div>
        ))}
      </div>
      <div className="thermalLegend">{data.thermal?.legend}</div>
    </div>
  );
}

function DesignRationale({ data }: { data: AnyRecord }) {
  return (
    <div className="rationale">
      <div className="sourceBanner">{data.intro}</div>
      <div className="rationaleGrid">
        {(data.sections || []).map((section: AnyRecord) => (
          <section className="rationaleSection" key={section.title}>
            <h3>{section.title}</h3>
            <ul>
              {(section.bullets || []).map((bullet: string) => (
                <li key={bullet}>{bullet}</li>
              ))}
            </ul>
          </section>
        ))}
      </div>
      <section className="formulaTable">
        <h3>Formula Checkpoints</h3>
        <table>
          <thead>
            <tr>
              <th>Checkpoint</th>
              <th>Formula</th>
              <th>Current Value</th>
            </tr>
          </thead>
          <tbody>
            {(data.formulas || []).map((row: AnyRecord) => (
              <tr key={row.checkpoint}>
                <td>{row.checkpoint}</td>
                <td>
                  <code>{row.formula}</code>
                </td>
                <td>{row.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

const HUMAN_LABELS: Record<string, string> = {
  input_voltage_min_v: "minimum input voltage",
  input_voltage_nominal_v: "nominal input voltage",
  input_voltage_max_v: "maximum input voltage",
  output_voltage_v: "output voltage",
  output_current_a: "output current",
  target_efficiency_percent: "target efficiency",
  ambient_temp_c: "ambient temperature",
  high_side_mosfet: "high-side MOSFET",
  low_side_mosfet: "low-side MOSFET",
  inductor: "inductor",
  input_capacitor: "input capacitor",
  output_capacitor: "output capacitor",
  hs_mosfet_conduction: "high-side MOSFET conduction-loss estimate",
  ls_mosfet_conduction: "low-side MOSFET conduction-loss estimate",
  hs_switching_overlap: "high-side MOSFET switching-loss estimate",
  inductor_dcr: "inductor copper-loss estimate",
  inductor_core_placeholder: "inductor core-loss estimate",
  output_cap_esr: "output capacitor ESR-loss estimate",
  input_cap_rms_esr: "input capacitor RMS-loss estimate"
};

const MISSING_EVIDENCE_MESSAGES: Record<string, string> = {
  thermal_result: "Thermal result is missing, so component temperature risk has not been checked.",
  "open_loop_sim.simulation_result": "Open-loop simulation result is missing, so waveform behavior has not been reviewed.",
  "simulation/waveforms/open_loop_waveforms.csv": "Exported waveform data file is missing, so simulation traces cannot be independently reviewed.",
  "closed_loop_control.control_result": "Closed-loop control result is missing, so stability and compensation have not been reviewed.",
  "pcb/schematic": "Schematic file is missing.",
  "pcb/layout": "PCB layout file is missing.",
  "pcb/drc_reports": "PCB design-rule check report is missing.",
  "pcb/erc_reports": "Schematic electrical-rule check report is missing.",
  "pcb/manufacturing/gerber": "Gerber manufacturing files are missing.",
  "pcb/manufacturing/drill": "PCB drill files are missing.",
  "pcb/manufacturing/cpl": "Component placement file is missing.",
  "firmware/generated": "Generated firmware source is missing.",
  "firmware/build": "Compiled firmware build is missing."
};

function humanLabel(value: string): string {
  return HUMAN_LABELS[value] || value.replace(/_/g, " ");
}

function humanizeRiskItem(item: string): string {
  const text = String(item);
  const mockPart = text.match(/^(.+) is sourced from mock catalog\.$/);
  if (mockPart) {
    return `The ${humanLabel(mockPart[1])} currently comes from a mock catalog and must be replaced with a verified supplier or datasheet-backed part.`;
  }
  if (text === "Blocked: risky hardware action requires --approve or HARDWARE_AGENT_APPROVAL=YES.") {
    return "Real hardware actions are blocked until a human explicitly approves manufacturing, firmware flashing, or lab execution.";
  }
  return text;
}

function humanizeMissingEvidence(item: string): string {
  const text = String(item);
  if (MISSING_EVIDENCE_MESSAGES[text]) return MISSING_EVIDENCE_MESSAGES[text];
  if (text.startsWith("spec.")) {
    return `The ${humanLabel(text.split(".")[1])} is not defined in the design specification.`;
  }
  if (text.startsWith("selected_bom.") && text.endsWith(".datasheet_url")) {
    const part = text.split(".")[1];
    return `The ${humanLabel(part)} datasheet link is missing, so the selected part cannot be verified.`;
  }
  if (text.startsWith("selected_bom.")) {
    const part = text.split(".")[1];
    return `The ${humanLabel(part)} has not been selected in the bill of materials.`;
  }
  if (text.startsWith("loss_breakdown.items_w.")) {
    const parts = text.split(".");
    const lossKey = parts[parts.length - 1] || text;
    return `The ${humanLabel(lossKey)} is missing from the loss model.`;
  }
  return text.replace(/_/g, " ").replace(/\//g, " / ").replace(/\./g, " - ");
}

function RiskSummary({ data }: { data: AnyRecord }) {
  const risks = (data.risks || []).map((item: string) => humanizeRiskItem(item));
  const missingEvidence = (data.missingData || []).map((item: string) => humanizeMissingEvidence(item));
  return (
    <div className="riskSummary">
      <div className="riskGrid">
        <section>
          <h3>Risks</h3>
          <ul className="compactList">{risks.map((item: string, index: number) => <li key={`${item}-${index}`}>{item}</li>)}</ul>
        </section>
        <section>
          <h3>Missing Evidence</h3>
          <ul className="compactList">{missingEvidence.map((item: string, index: number) => <li key={`${item}-${index}`}>{item}</li>)}</ul>
        </section>
        <section>
          <h3>Next Actions</h3>
          <ul className="compactList">{(data.recommendedNextActions || []).map((item: string) => <li key={item}>{item}</li>)}</ul>
        </section>
      </div>
    </div>
  );
}

function selectedSampleId(projectRequest: string): string {
  return DEMO_PROJECT_REQUESTS.find((sample) => sample.request === projectRequest)?.id || "diy";
}

function localStorageBoolean(key: string, fallback: boolean): boolean {
  if (typeof window === "undefined") return fallback;
  const value = window.localStorage.getItem(key);
  return value === null ? fallback : value === "true";
}

function useStoredBoolean(key: string, fallback: boolean): [boolean, (value: boolean) => void] {
  const [value, setValue] = React.useState(() => localStorageBoolean(key, fallback));
  const update = React.useCallback((next: boolean) => {
    setValue(next);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(key, String(next));
    }
  }, [key]);
  return [value, update];
}

function EngineeringSidebar({
  state,
  actions,
  notice,
  projectRequest,
  onProjectRequestChange,
  plan,
  collapsed,
  onToggle,
}: {
  state: AnyRecord;
  actions: AnyRecord;
  notice: string;
  projectRequest: string;
  onProjectRequestChange: (request: string) => void;
  plan: WorkflowPlan;
  collapsed: boolean;
  onToggle: () => void;
}) {
  const selectedSample = selectedSampleId(projectRequest);
  const events = (state.progressEvents || []).slice(-12).reverse();
  const navItems = ["Project", "Specs", "Modules", "Artifacts", "Validation", "Logs", "Settings"];
  if (collapsed) {
    return (
      <aside className="engineeringSidebar collapsed" aria-label="Collapsed engineering navigation">
        <button className="panelToggle" onClick={onToggle} title="Expand files panel" aria-label="Expand files panel">›</button>
        <div className="brandMark compactOnly">AE</div>
        <nav className="collapsedNav" aria-label="Compact engineering navigation">
          {navItems.map((item, index) => (
            <button className={index === 0 ? "active" : ""} key={item} title={item}>
              {item.slice(0, 1)}
            </button>
          ))}
        </nav>
        <button className="collapsedRun" onClick={() => actions.runDemo(demoRunPayload(plan))} disabled={state.running} title="Run Demo">
          {state.running ? "…" : "▶"}
        </button>
      </aside>
    );
  }

  return (
    <aside className="engineeringSidebar">
      <button className="panelToggle sideToggle" onClick={onToggle} title="Collapse files panel" aria-label="Collapse files panel">‹</button>
      <div className="brandBlock compactBrand">
        <div className="brandMark">AE</div>
        <div>
          <div className="brandTitle">AutoEE</div>
          <div className="brandSubtitle">Engineering Console</div>
        </div>
      </div>

      <label className="requestSelector compactSelector">
        <span>Project Request</span>
        <select
          value={selectedSample}
          onChange={(event) => {
            if (event.target.value === "diy") {
              onProjectRequestChange("");
              return;
            }
            const next = DEMO_PROJECT_REQUESTS.find((sample) => sample.id === event.target.value);
            if (next) onProjectRequestChange(next.request);
          }}
        >
          <option value="diy">DIY Request</option>
          {DEMO_PROJECT_REQUESTS.map((sample) => (
            <option value={sample.id} key={sample.id}>
              {sample.label}
            </option>
          ))}
        </select>
      </label>
      {selectedSample === "diy" && (
        <textarea
          className="diyRequestInput compactInput"
          value={projectRequest === DIY_REQUEST_FALLBACK ? "" : projectRequest}
          placeholder="Describe the hardware project..."
          rows={4}
          onChange={(event) => onProjectRequestChange(event.target.value)}
        />
      )}

      <nav className="engineeringNav" aria-label="Engineering console navigation">
        {navItems.map((item, index) => (
          <button className={index === 0 ? "active" : ""} key={item}>
            {item}
          </button>
        ))}
      </nav>

      <div className="engineeringRunBox">
        <button className="primary" onClick={() => actions.runDemo(demoRunPayload(plan))} disabled={state.running}>
          {state.running ? "Running..." : "Run Demo"}
        </button>
        <button onClick={actions.stop} disabled={!state.running}>Stop</button>
        <button onClick={actions.reset}>Reset</button>
      </div>
      {notice && <div className="notice compactNotice">{notice}</div>}

      <details className="logsDisclosure">
        <summary>Logs</summary>
        <div className="eventList compactLogs">
          {events.length ? events.map((event: AnyRecord, index: number) => (
            <div className="eventItem" key={`${event.timestamp}-${index}`}>
              <span>{event.module_id}</span>
              <strong>{event.status}</strong>
              <p>{event.message}</p>
            </div>
          )) : <div className="empty">No workflow events.</div>}
        </div>
      </details>

      <div className="sidebarMeta">
        <span>{domainName(plan.classification.primaryDomain)}</span>
        <strong>{plan.classification.productType.replace(/_/g, " ")}</strong>
      </div>
    </aside>
  );
}

function EngineeringProjectHeader({
  state,
  actions,
  plan,
  onOpenInvestor,
  darkTheme,
  onSetDarkTheme,
}: {
  state: AnyRecord;
  actions: AnyRecord;
  plan: WorkflowPlan;
  onOpenInvestor: () => void;
  darkTheme: boolean;
  onSetDarkTheme: (enabled: boolean) => void;
}) {
  const spec = state.spec || state.rawState?.spec || {};
  const profile = demoProfileForPlan(plan);
  const statusStages = state.demoMode === "profile_fake" ? (state.activeDemoStages || []) : (state.stages || []);
  const completed = statusStages.filter((stage: AnyRecord) => stage.status === "complete").length;
  const total = statusStages.length || plan.workflowSteps.length;
  const status = state.workflowStatus === "complete" ? "Needs Review" : state.running ? "Running" : "Ready";
  const projectName = plan.classification.primaryDomain === "power_electronics"
    ? String(spec.name || profile.projectName).replace(/^AutoEE\s+/i, "").replace(/\s+Demo$/i, "")
    : profile.projectName;
  return (
    <header className="projectHeader">
      <div>
        <span className="projectKicker">Project</span>
        <h1>{projectName}</h1>
        <div className="projectMeta">
          <span>{domainName(plan.classification.primaryDomain)}</span>
          <span>{profile.circuitName}</span>
          <span>{completed} / {total} modules complete</span>
        </div>
      </div>
      <div className="projectStatusBlock">
        <span className={`projectStatus ${status.toLowerCase().replace(/\s+/g, "-")}`}>{status}</span>
        <div className="projectActions">
          <button className="primary" onClick={() => actions.runDemo(demoRunPayload(plan))} disabled={state.running}>{state.running ? "Running..." : "Run Demo"}</button>
          <button disabled>Run Module</button>
          <button onClick={actions.exportSnapshot}>Export Package</button>
          <div className="themeSwitch" aria-label="Engineering Console theme">
            <button className={!darkTheme ? "active" : ""} onClick={() => onSetDarkTheme(false)}>Day</button>
            <button className={darkTheme ? "active" : ""} onClick={() => onSetDarkTheme(true)}>Night</button>
          </div>
          <button onClick={onOpenInvestor}>Home Page</button>
        </div>
      </div>
    </header>
  );
}

const INVESTOR_FLOW = [
  {
    title: "Understand",
    caption: "Read specs",
    sourceStageIds: ["understand_specs"],
    icon: "file",
  },
  {
    title: "Plan",
    caption: "Choose modules",
    sourceStageIds: ["select_parts"],
    icon: "chip",
  },
  {
    title: "Generate",
    caption: "Create artifacts",
    sourceStageIds: ["loss_thermal", "waveforms", "control", "package"],
    icon: "board",
  },
  {
    title: "Review",
    caption: "Surface risks",
    sourceStageIds: ["test_report", "package"],
    icon: "report",
  },
];

const INVESTOR_PACKAGE_CARDS = [
  ["BOM", "Supplier-aware part list", "chip", ["select_parts"]],
  ["Schematic Draft", "Reviewable circuit intent", "file", ["package"]],
  ["Layout Rules", "PCB constraints and guardrails", "board", ["package"]],
  ["Simulation Preview", "Behavior before bench time", "activity", ["waveforms"]],
  ["Risk Report", "What still needs proof", "report", ["package"]],
  ["Engineer Review Checklist", "Ready for human signoff", "report", ["test_report", "package"]],
] as const;

const HERO_PACKAGE_CHIPS = [
  ["BOM", "chip"],
  ["Schematic", "file"],
  ["Layout", "board"],
  ["Simulation", "activity"],
  ["Risk", "report"],
  ["Checklist", "report"],
] as const;

const PLATFORM_DOMAINS = [
  ["Power", "First wedge", "activity"],
  ["Communication", "Wireless", "chart"],
  ["Sensing", "Signals", "sliders"],
  ["Embedded", "Firmware", "code"],
  ["High-Speed", "Systems", "board"],
  ["Mechanical", "Physical design", "board"],
] as const;

function InvestorStoryPage({
  state,
  actions,
  plan,
  onOpenEngineering,
}: {
  state: AnyRecord;
  actions: AnyRecord;
  plan: WorkflowPlan;
  onOpenEngineering: () => void;
}) {
  return (
    <div className="investorStory">
      <section className="storyHero">
        <div className="storyHeroCopy">
          <span className="storyEyebrow">AI-Native Hardware Platform</span>
          <h1>Specs → Hardware</h1>
          <p>AI-Powered Autonomous Hardware Design</p>
          <div className="storyActions">
            <button className="storyPrimary" onClick={() => actions.runDemo()} disabled={state.running}>
              {state.running ? "Running..." : "Run Demo"}
            </button>
            <button className="storySecondary" onClick={onOpenEngineering}>
              Engineering Console
            </button>
          </div>
        </div>
        <div className="storyHeroVisual">
          <img src="/pcb-closeup-home.jpg" alt="PCB electronics close-up" />
          <div className="packageGlowCard">
            <span>Ready to Review</span>
            <strong>Hardware Design Package</strong>
            <div className="heroArtifactList">
              {HERO_PACKAGE_CHIPS.map(([title, icon]) => (
                <small key={title}>
                  <RoadmapIcon name={icon} />
                  {title}
                </small>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="storySection transformSection">
        <div className="storySectionHeader">
          <span>How It Works</span>
          <h2>Spec → Package</h2>
        </div>
        <div className="transformationFlow">
          <article className="transformCard">
            <span className="transformIcon"><RoadmapIcon name="file" /></span>
            <h3>Spec</h3>
            <p>Product request</p>
          </article>
          <div className="flowArrow" aria-hidden="true">→</div>
          <article className="transformCard agentCard">
            <span className="transformIcon"><RoadmapIcon name="activity" /></span>
            <h3>Agent</h3>
            <p>Plans workflow</p>
          </article>
          <div className="flowArrow" aria-hidden="true">→</div>
          <article className="transformCard">
            <span className="transformIcon"><RoadmapIcon name="report" /></span>
            <h3>Package</h3>
            <p>Ready to review</p>
          </article>
        </div>
      </section>

      <section className="storySection">
        <div className="storySectionHeader">
          <span>AI Workflow</span>
          <h2>Simple 4-Step Flow</h2>
        </div>
        <div className="simpleWorkflow">
          {INVESTOR_FLOW.map((item, index) => {
            const status = sourceStatus(combinedStagePayloads(state), item.sourceStageIds);
            return (
              <article className={`simpleStep status-${status}`} key={item.title}>
                <div>
                  <span>{index + 1}</span>
                  <StatusDot status={status} />
                </div>
                <RoadmapIcon name={item.icon} />
                <h3>{item.title}</h3>
                <p>{item.caption}</p>
              </article>
            );
          })}
        </div>
      </section>

      <section className="storySection">
        <div className="storySectionHeader">
          <span>Preview</span>
          <h2>Review Kit</h2>
        </div>
        <div className="storyPackageGrid">
          {INVESTOR_PACKAGE_CARDS.map(([title, caption, icon, sourceStageIds]) => {
            const status = sourceStatus(combinedStagePayloads(state), sourceStageIds);
            return (
              <article className={`storyPackageCard status-${status}`} key={title}>
                <span><RoadmapIcon name={icon} /></span>
                <h3>{title}</h3>
                <p>{caption}</p>
              </article>
            );
          })}
        </div>
      </section>

      <section className="storySection platformSection">
        <div className="storySectionHeader">
          <span>Platform Expansion</span>
          <h2>Start with power. Extend the workflow across hardware.</h2>
        </div>
        <div className="platformRail">
          {PLATFORM_DOMAINS.map(([title, caption, icon], index) => (
            <React.Fragment key={title}>
              <article className={index === 0 ? "current" : ""}>
                <b>{index + 1}</b>
                <span><RoadmapIcon name={icon} /></span>
                <strong>{title}</strong>
                {index === 0 ? <em>{caption}</em> : <small>{caption}</small>}
              </article>
              {index < PLATFORM_DOMAINS.length - 1 && <i aria-hidden="true">↓</i>}
            </React.Fragment>
          ))}
        </div>
      </section>
    </div>
  );
}

function InvestorPosterPage({
  state,
  actions,
  onOpenEngineering,
}: {
  state: AnyRecord;
  actions: AnyRecord;
  onOpenEngineering: () => void;
}) {
  const processItems = ["Spec", "Understand", "Plan", "Generate", "Review", "Package"];
  const domains = ["Power", "Communication", "Sensing", "Embedded", "High-Speed", "Mechanical"];
  return (
    <div className="investorPoster">
      <section className="posterStage">
        <div className="posterCopy">
          <span>AI-Native Hardware Platform</span>
          <h1>Specs → Hardware</h1>
          <p>AI-Powered Autonomous Hardware Design</p>
          <div className="storyActions">
            <button className="storyPrimary" onClick={() => actions.runDemo()} disabled={state.running}>
              {state.running ? "Running..." : "Run Demo"}
            </button>
            <button className="storySecondary" onClick={onOpenEngineering}>
              Engineering Console
            </button>
          </div>
        </div>

        <div className="posterPackage">
          <div className="packageBackdrop" />
          <section>
            <span>Reviewable output</span>
            <h2>Hardware Design Package</h2>
            <p>BOM &middot; Schematic &middot; Layout &middot; Simulation &middot; Risk &middot; Checklist</p>
            <div className="packageArtifactLine">
              {HERO_PACKAGE_CHIPS.map(([title]) => <strong key={title}>{title}</strong>)}
            </div>
          </section>
        </div>
      </section>

      <div className="posterProcessRail" aria-label="Requirement to design package process">
        {processItems.map((item, index) => (
          <React.Fragment key={item}>
            <span className={index === 0 || index === processItems.length - 1 ? "edge" : ""}>{item}</span>
            {index < processItems.length - 1 && <i aria-hidden="true">→</i>}
          </React.Fragment>
        ))}
      </div>

      <section className="posterPlatformBand">
        <p>Power first. Expand across hardware.</p>
        <div>
          {domains.map((item, index) => (
            <React.Fragment key={item}>
              <span className={index === 0 ? "first" : ""}>{item}{index === 0 && <em>First wedge</em>}</span>
              {index < domains.length - 1 && <i aria-hidden="true">→</i>}
            </React.Fragment>
          ))}
        </div>
      </section>
    </div>
  );
}

function InvestorLandingPage({
  state,
  onRunDemo,
}: {
  state: AnyRecord;
  onRunDemo: () => void;
}) {
  const domains = ["Power", "Communication", "Sensing", "Embedded", "High-Speed", "Mechanical"];
  const [showConsolePreview, setShowConsolePreview] = React.useState(false);

  return (
    <div className="investorLanding">
      <section className={`landingHero ${showConsolePreview ? "console-visible" : "console-hidden"}`}>
        <div className="landingHeroMedia" aria-hidden="true" />
        <div className="landingHeroShade" aria-hidden="true" />
        <div className="landingHeroCopy">
          <span>AI-Native Hardware Platform</span>
          <h1>
            <strong>AutoEE</strong>
            <em>Specs &rarr; Hardware</em>
          </h1>
          <p>AI-Powered Autonomous Hardware Design</p>
          <div className="landingActions">
            <button className="storyPrimary" onClick={onRunDemo} disabled={state.running}>
              {state.running ? "Running..." : "Run Demo"}
            </button>
            <button
              className="storySecondary"
              onClick={() => setShowConsolePreview((visible) => !visible)}
              aria-expanded={showConsolePreview}
            >
              Show Concept
            </button>
          </div>
        </div>

        {showConsolePreview && (
          <figure className="landingConsolePreview">
            <img src="/Example%20Engineering%20Console.png" alt="Example Engineering Console preview" />
          </figure>
        )}
      </section>

      <section className="landingPlatform">
        <div>
          <h2>Power first. General hardware next.</h2>
          <div className="landingDomainStack" aria-label="AutoEE hardware domain expansion path">
            {domains.map((item, index) => (
              <React.Fragment key={item}>
                <span>{item}</span>
                {index < domains.length - 1 && <i aria-hidden="true">&rarr;</i>}
              </React.Fragment>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

function AgentStatusRail({ state }: { state: AnyRecord }) {
  const complete = state.workflowStatus === "complete";
  const running = Boolean(state.running);
  const statusText = running ? "Running" : complete ? "Done" : "Ready";
  return (
    <div className={`agentStatusRail ${running ? "running" : complete ? "done" : "ready"}`}>
      <span aria-hidden="true" />
      <strong>{statusText}</strong>
    </div>
  );
}

function EngineeringRightPanel({
  state,
  actions,
  plan,
  collapsed,
  onToggle,
}: {
  state: AnyRecord;
  actions: AnyRecord;
  plan: WorkflowPlan;
  collapsed: boolean;
  onToggle: () => void;
}) {
  if (collapsed) {
    return (
      <aside className="copilotRail" aria-label="Collapsed agent panel">
        <button className="panelToggle" onClick={onToggle} title="Expand agent panel" aria-label="Expand agent panel">‹</button>
        <span className="copilotRailLabel">Agent</span>
        <AgentStatusRail state={state} />
        <button className="copilotRailAction" onClick={actions.exportSnapshot} title="Export package">⇩</button>
      </aside>
    );
  }

  return (
    <aside className="rightStack agentPanel">
      <button className="panelToggle sideToggle rightSideToggle" onClick={onToggle} title="Collapse agent panel" aria-label="Collapse agent panel">›</button>
      <AgentStatusRail state={state} />
      <ArtifactPackage state={state} actions={actions} plan={plan} showSpecEditor />
      <EvidenceRail state={state} />
    </aside>
  );
}

function App() {
  const { state, actions, notice } = useAutoEEState();
  const [mode, setMode] = React.useState("engineering");
  const [leftPanelOpen, setLeftPanelOpen] = useStoredBoolean("autoee.engineering.leftPanelOpen", true);
  const [rightPanelOpen, setRightPanelOpen] = useStoredBoolean("autoee.engineering.rightPanelOpen", true);
  const [darkEngineeringTheme, setDarkEngineeringTheme] = useStoredBoolean("autoee.engineering.darkTheme", false);
  const [projectRequest, setProjectRequest] = React.useState(DEFAULT_PROJECT_REQUEST);
  const initializedProjectRequest = React.useRef(false);
  const activeProjectRequest = projectRequest.trim() || DIY_REQUEST_FALLBACK;
  const plan = React.useMemo(() => planWorkflow(activeProjectRequest), [activeProjectRequest]);
  const runPowerInvestorDemo = React.useCallback(() => {
    const powerRequest = DEMO_PROJECT_REQUESTS[0]?.request || DEFAULT_PROJECT_REQUEST;
    const powerPlan = planWorkflow(powerRequest);
    setProjectRequest(powerRequest);
    setMode("engineering");
    void actions.runDemo(demoRunPayload(powerPlan));
  }, [actions]);
  React.useEffect(() => {
    if (!initializedProjectRequest.current && state.prompt) {
      initializedProjectRequest.current = true;
      if (projectRequest !== DEFAULT_PROJECT_REQUEST) {
        setProjectRequest(state.prompt);
      }
    }
  }, [projectRequest, state.prompt]);
  React.useEffect(() => {
    const failures = [...validateWorkflowPlannerSamples(), ...validateDemoCircuitProfiles()];
    if (failures.length) {
      console.warn("Workflow planner sample validation failed:", failures);
    }
  }, []);
  if (mode === "investor") {
    return (
      <div className="appShell storyShell">
        <main className="main storyMain">
          <div className="storyTopbar">
            <div className="brandBlock">
              <div className="brandMark">AE</div>
              <div>
                <div className="brandTitle">AutoEE</div>
                <div className="brandSubtitle">AI Hardware Agent</div>
              </div>
            </div>
            <div className="modeTabs">
              <button className="active" onClick={() => setMode("investor")}>
                Home Page
              </button>
              <button onClick={() => setMode("engineering")}>
                Engineering Console
              </button>
            </div>
          </div>
          {notice && <div className="notice storyNotice">{notice}</div>}
          <InvestorLandingPage state={state} onRunDemo={runPowerInvestorDemo} />
        </main>
      </div>
    );
  }

  return (
    <div className={`appShell engineeringShell ${leftPanelOpen ? "left-open" : "left-collapsed"} ${darkEngineeringTheme ? "theme-dark" : "theme-light"}`}>
      <EngineeringSidebar
        state={state}
        actions={actions}
        notice={notice}
        projectRequest={activeProjectRequest}
        onProjectRequestChange={setProjectRequest}
        plan={plan}
        collapsed={!leftPanelOpen}
        onToggle={() => setLeftPanelOpen(!leftPanelOpen)}
      />
      <main className="main engineeringMain">
        <EngineeringProjectHeader
          state={state}
          actions={actions}
          plan={plan}
          onOpenInvestor={() => setMode("investor")}
          darkTheme={darkEngineeringTheme}
          onSetDarkTheme={setDarkEngineeringTheme}
        />
        <div className={`mainGrid engineeringGrid ${rightPanelOpen ? "right-open" : "right-collapsed"}`}>
          <div className="centerStack">
            <ProjectUnderstanding plan={plan} />
            <StageTimeline state={state} plan={plan} />
            <ModuleSelectionPanel plan={plan} />
            <DynamicMetricsPanel state={state} plan={plan} />
            <EngineeringTabs state={state} plan={plan} />
          </div>
          <EngineeringRightPanel
            state={state}
            actions={actions}
            plan={plan}
            collapsed={!rightPanelOpen}
            onToggle={() => setRightPanelOpen(!rightPanelOpen)}
          />
        </div>
      </main>
    </div>
  );
}

export default App;
