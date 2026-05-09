import React from "react";

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
  evidenceBadges: [],
  progressEvents: [],
  rawState: {}
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
  if (!metric) return "-";
  return String(metric.display ?? metric.label ?? metric.value ?? "-");
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
    runDemo: async () => {
      setNotice("");
      const payload = await postJson("/api/run-demo");
      setState(payload.state);
    },
    stop: async () => {
      const payload = await postJson("/api/stop");
      setState(payload.state);
    },
    reset: async () => {
      setNotice("");
      const payload = await postJson("/api/reset");
      setState(payload.state);
    },
    exportSnapshot: async () => {
      const payload = await postJson("/api/export-snapshot");
      setState(payload.state);
      setNotice(`Snapshot exported: ${payload.path}`);
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

function LeftRail({ state, actions, notice }: { state: AnyRecord; actions: AnyRecord; notice: string }) {
  const events = (state.progressEvents || []).slice(-8).reverse();
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
        <p>{state.prompt}</p>
      </div>

      <div className="buttonGrid">
        <button className="primary" onClick={actions.runDemo} disabled={state.running}>
          {state.running ? "Running..." : "Run 3-Min Demo"}
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

function Hero({ state }: { state: AnyRecord }) {
  const metrics = state.metrics || {};
  return (
    <section className="hero">
      <div>
        <div className="eyebrow">Investor Demo Mode</div>
        <h1>Specification → Verified Hardware</h1>
        <p>AI-generated hardware draft: specs, BOM, waveforms, control, risks, and package.</p>
      </div>
      <div className="productVision">
        <img src="/pcb-closeup-home.jpg" alt="PCB electronics close-up" />
        <div className="productVisionCaption">
          <span>Target Outcome</span>
          <strong>Manufacturable charger PCB package</strong>
        </div>
      </div>
      <div className="heroMetrics">
        <MetricTile label="Efficiency" metric={metrics.efficiency} />
        <MetricTile label="Loss" metric={metrics.totalLoss} />
        <MetricTile label="Hot Spot" metric={metrics.maxTemp} />
        <MetricTile label="Ripple" metric={metrics.voutRipple} />
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

function StageTimeline({ stages }: { stages: AnyRecord[] }) {
  return (
    <section className="panel">
      <div className="panelHeader">
        <div>
          <h2>System Map</h2>
          <p>From request to hardware package.</p>
        </div>
      </div>
      <div className="stageGrid">
        {stages.map((stage) => (
          <div className={`stageCard ${clsStatus(stage.status)}`} key={stage.id}>
            <div className="stageTopline">
              <span className="stageIndex">{stage.index}</span>
              <StatusPill status={stage.status} />
            </div>
            <h3>{stage.title}</h3>
          </div>
        ))}
      </div>
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

function DesignPackage({ state, actions }: { state: AnyRecord; actions: AnyRecord }) {
  const stages = state.stages || [];
  const spec = state.spec || state.rawState?.spec || {};
  const [draft, setDraft] = React.useState<AnyRecord>(() => toEditableSpec(spec));
  const [error, setError] = React.useState("");
  const [dirty, setDirty] = React.useState(false);
  React.useEffect(() => {
    if (!dirty) {
      setDraft(toEditableSpec(spec));
      setError("");
    }
  }, [JSON.stringify(spec), dirty]);
  const ready = stages.length > 0 && stages.every((stage: AnyRecord) => stage.status === "complete");
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
          <h2>{ready ? "Design Package Ready" : "Design Package"}</h2>
          <p>Edit specs, then rerun the agent.</p>
        </div>
      </div>
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
      <div className="packageSubhead">Generated Package</div>
      <div className="packageList">
        {stages.map((stage: AnyRecord) => (
          <div className="packageItem" key={stage.id}>
            <StatusDot status={stage.status} />
            <div>
              <strong>{stage.generatedArtifact}</strong>
              <span>{stage.evidenceLevel}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function StatusDot({ status }: { status: string }) {
  return <span className={`statusDot ${String(status || "waiting")}`} />;
}

function EnergyStory({ state }: { state: AnyRecord }) {
  return (
    <section className="panel">
      <div className="panelHeader">
        <div>
          <h2>Energy Story</h2>
          <p>Power, heat, and stability at a glance.</p>
        </div>
      </div>
      <div className="energyGrid">
        {(state.energy?.cards || []).map((card: AnyRecord) => (
          <div className={`energyCard tone-${card.tone || "neutral"}`} key={card.label}>
            <span>{card.label}</span>
            <strong>{card.display}</strong>
          </div>
        ))}
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
            <span>Missing data</span>
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

function EngineeringTabs({ state }: { state: AnyRecord }) {
  const [tab, setTab] = React.useState("waveforms");
  const tabs = [
    ["waveforms", "Waveforms"],
    ["loss", "Loss/Thermal"],
    ["rationale", "Design Rationale"],
    ["risk", "Risk Summary"],
    ["json", "Developer State"]
  ];
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

function RiskSummary({ data }: { data: AnyRecord }) {
  return (
    <div className="riskSummary">
      <div className="riskGrid">
        <section>
          <h3>Risks</h3>
          <ul className="compactList">{(data.risks || []).map((item: string) => <li key={item}>{item}</li>)}</ul>
        </section>
        <section>
          <h3>Missing Data</h3>
          <ul className="compactList">{(data.missingData || []).map((item: string) => <li key={item}>{item}</li>)}</ul>
        </section>
        <section>
          <h3>Next Actions</h3>
          <ul className="compactList">{(data.recommendedNextActions || []).map((item: string) => <li key={item}>{item}</li>)}</ul>
        </section>
      </div>
    </div>
  );
}

function App() {
  const { state, actions, notice } = useAutoEEState();
  const [mode, setMode] = React.useState("investor");
  return (
    <div className="appShell">
      <LeftRail state={state} actions={actions} notice={notice} />
      <main className="main">
        <div className="modeTabs">
          <button className={mode === "investor" ? "active" : ""} onClick={() => setMode("investor")}>
            Investor Demo
          </button>
          <button className={mode === "engineering" ? "active" : ""} onClick={() => setMode("engineering")}>
            Engineering Console
          </button>
        </div>
        {mode === "investor" ? (
          <>
            <Hero state={state} />
            <div className="mainGrid">
              <div className="centerStack">
                <StageTimeline stages={state.stages || []} />
                <EnergyStory state={state} />
                <EngineeringTabs state={state} />
              </div>
              <div className="rightStack">
                <DesignPackage state={state} actions={actions} />
                <EvidenceRail state={state} />
              </div>
            </div>
          </>
        ) : (
          <>
            <Hero state={state} />
            <EngineeringTabs state={state} />
          </>
        )}
      </main>
    </div>
  );
}

export default App;
