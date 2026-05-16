from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from autoee_demo.core.state import DesignState
from autoee_demo.model_backend import ModelManager

from .base import AutoEESkill, SkillRunResult, require_result


def _notice(specific: str) -> str:
    return f"Demo data only. {specific} is not connected to real bench hardware yet."


def _base_payload(source_type: str, notice: str) -> Dict[str, Any]:
    return {
        "sourceType": source_type,
        "realCapabilityStatus": "not_connected",
        "signoffStatus": "not_signoff_demo_result",
        "notice": notice,
    }


class EmbeddedCodingDownloadSkill(AutoEESkill):
    module_id = "embedded_coding_download"
    title = "Embedded Coding Download"
    description = "Fake firmware build, flash, and bring-up evidence for the returned prototype."

    def run(
        self,
        state: DesignState,
        model_manager: Optional[ModelManager] = None,
        output_dir: Optional[Path] = None,
    ) -> SkillRunResult:
        require_result(state, "library_pcb_mechanical")
        spec = state.spec
        firmware_artifact = "firmware/build/AutoEE_usb_c_buck_fw_v0.3.0_demo.hex"
        data = {
            **_base_payload(
                "fake_firmware_flash",
                _notice("Firmware generation, build, flashing, and target communication"),
            ),
            "status": "demo_complete",
            "targetBoard": "AutoEE USB-C buck prototype revA",
            "firmwareArtifact": firmware_artifact,
            "firmwareVersion": "v0.3.0-demo",
            "programmer": "SWD/J-Link demo adapter",
            "deviceIdentity": {
                "mcu": "STM32G431CBU6",
                "boardId": "AutoEE-BUCK-REV-A-FAKE",
                "serial": "DEMO-LAB-0007",
            },
            "configuration": {
                "vinRange": f"{spec.input_voltage_min_v:g}-{spec.input_voltage_max_v:g} V",
                "voutTarget": f"{spec.output_voltage_v:g} V",
                "currentLimit": f"{spec.output_current_a * 1.25:.2f} A",
                "telemetryRateHz": 2000,
            },
            "flashLog": [
                {
                    "step": "Generate firmware project",
                    "status": "demo_pass",
                    "detail": "Control registers, ADC channels, protection thresholds, and telemetry map are emitted from the design state.",
                },
                {
                    "step": "Build firmware image",
                    "status": "demo_pass",
                    "detail": f"Compiled demo image {firmware_artifact}. No real compiler invocation in this version.",
                },
                {
                    "step": "Program prototype",
                    "status": "demo_pass",
                    "detail": "Fake flash transcript records erase, program, verify, and reset phases.",
                },
                {
                    "step": "Bring-up handshake",
                    "status": "demo_pass",
                    "detail": "Fake UART/SWD telemetry confirms board identity and boot state.",
                },
            ],
            "outputs": [
                {"label": "Firmware image", "path": f"fake://{firmware_artifact}"},
                {"label": "Flash transcript", "path": "fake://firmware/logs/flash_revA_0007.txt"},
                {"label": "Register map", "path": "fake://firmware/generated/control_register_map.json"},
            ],
            "realIntegrationPoints": [
                "Firmware template generator",
                "CMake or vendor IDE build",
                "OpenOCD, J-Link, or STM32CubeProgrammer CLI",
                "Serial/SWD telemetry reader",
            ],
        }
        return self.complete(
            state,
            SkillRunResult(
                self.module_id,
                self.title,
                "Generated fake firmware build, flash log, and target bring-up evidence.",
                data,
                source="fake_lab_adapter",
            ),
        )


class ClosedLoopTuningSkill(AutoEESkill):
    module_id = "closed_loop_tuning"
    title = "Auto Closed-Loop Tuning"
    description = "Fake bench tuning sweep that refines the analytical control seed."

    def run(
        self,
        state: DesignState,
        model_manager: Optional[ModelManager] = None,
        output_dir: Optional[Path] = None,
    ) -> SkillRunResult:
        control_result = require_result(state, "closed_loop_control")
        require_result(state, "embedded_coding_download")
        control = control_result["control_result"]
        initial = {
            "kp": control["kp"],
            "ki": control["ki"],
            "kd": control["kd"],
            "kf": control["kf"],
        }
        sweep = [
            {
                "iteration": 1,
                "kp": round(float(initial["kp"]) * 0.82, 7),
                "ki": round(float(initial["ki"]) * 0.78, 4),
                "settlingMs": 0.84,
                "overshootPercent": 5.9,
                "phaseMarginDeg": 49.0,
                "status": "demo_review",
            },
            {
                "iteration": 2,
                "kp": round(float(initial["kp"]) * 0.95, 7),
                "ki": round(float(initial["ki"]) * 0.9, 4),
                "settlingMs": 0.58,
                "overshootPercent": 3.4,
                "phaseMarginDeg": 56.0,
                "status": "demo_pass",
            },
            {
                "iteration": 3,
                "kp": round(float(initial["kp"]) * 1.03, 7),
                "ki": round(float(initial["ki"]) * 0.94, 4),
                "settlingMs": 0.46,
                "overshootPercent": 2.2,
                "phaseMarginDeg": 61.0,
                "status": "demo_selected",
            },
        ]
        selected = sweep[-1]
        data = {
            **_base_payload(
                "fake_closed_loop_bench_tuning",
                _notice("Electronic load, scope, power analyzer, and live compensator update loop"),
            ),
            "status": "demo_complete",
            "controlMode": "Voltage-mode synchronous buck",
            "objective": "Minimize load-step error while preserving phase margin and avoiding excessive duty-cycle command noise.",
            "initialParameters": initial,
            "selectedParameters": {
                "kp": selected["kp"],
                "ki": selected["ki"],
                "kd": initial["kd"],
                "kf": initial["kf"],
            },
            "parameterSweep": sweep,
            "benchResponse": {
                "targetSettlingMs": state.spec.transient_settling_ms,
                "targetDeviationMv": state.spec.transient_deviation_mv,
                "measuredSettlingMs": selected["settlingMs"],
                "measuredDeviationMv": 118.0,
                "phaseMarginDeg": selected["phaseMarginDeg"],
            },
            "validation": [
                {"check": "Load-step settling", "target": "<= 1.0 ms", "result": "0.46 ms", "status": "demo_pass"},
                {"check": "Peak deviation", "target": "<= 250 mV", "result": "118 mV", "status": "demo_pass"},
                {"check": "Phase margin", "target": ">= 45 deg", "result": "61 deg", "status": "demo_pass"},
                {"check": "Signoff", "target": "Measured bench evidence", "result": "Demo data only", "status": "not_signoff"},
            ],
            "outputs": [
                {"label": "Tuning sweep", "path": "fake://lab/tuning/closed_loop_sweep_revA.csv"},
                {"label": "Final control registers", "path": "fake://firmware/generated/final_control_registers.json"},
                {"label": "Load-step plot", "path": "fake://lab/plots/load_step_after_tuning.png"},
            ],
            "realIntegrationPoints": [
                "Programmable load control",
                "Oscilloscope waveform capture",
                "Live firmware parameter update",
                "Autotune optimizer with safety bounds",
            ],
        }
        return self.complete(
            state,
            SkillRunResult(
                self.module_id,
                self.title,
                "Produced fake closed-loop tuning sweep and selected demo compensator settings.",
                data,
                source="fake_lab_adapter",
            ),
        )


class EfficiencyLoggingSkill(AutoEESkill):
    module_id = "efficiency_logging"
    title = "Auto Efficiency Logging"
    description = "Fake efficiency, ripple, temperature, and bench metadata logging."

    def run(
        self,
        state: DesignState,
        model_manager: Optional[ModelManager] = None,
        output_dir: Optional[Path] = None,
    ) -> SkillRunResult:
        require_result(state, "closed_loop_tuning")
        loss = require_result(state, "loss_thermal")["loss_breakdown"]
        spec = state.spec
        efficiency_points: List[Dict[str, Any]] = [
            {
                "vinV": 12.0,
                "loadA": 0.30,
                "voutV": 5.03,
                "inputPowerW": 1.62,
                "outputPowerW": 1.51,
                "efficiencyPercent": 93.0,
                "hotSpotC": 63.5,
                "rippleMvpp": 19.0,
            },
            {
                "vinV": 12.0,
                "loadA": 1.00,
                "voutV": 5.02,
                "inputPowerW": 5.36,
                "outputPowerW": 5.02,
                "efficiencyPercent": 93.7,
                "hotSpotC": 71.2,
                "rippleMvpp": 26.0,
            },
            {
                "vinV": 12.0,
                "loadA": 2.00,
                "voutV": 5.01,
                "inputPowerW": 10.70,
                "outputPowerW": 10.02,
                "efficiencyPercent": 93.6,
                "hotSpotC": 84.4,
                "rippleMvpp": 35.0,
            },
            {
                "vinV": 12.0,
                "loadA": 3.00,
                "voutV": 5.00,
                "inputPowerW": 16.08,
                "outputPowerW": 15.00,
                "efficiencyPercent": float(loss.get("efficiency_percent", 93.28)),
                "hotSpotC": 97.5,
                "rippleMvpp": 42.0,
            },
        ]
        summary_cards = [
            {"label": "Full-load efficiency", "value": "93.28%", "status": "demo_pass", "note": "Fake bench point at 12 V input and 3 A load."},
            {"label": "Peak efficiency", "value": "93.7%", "status": "demo_pass", "note": "Fake sweep peak near 1 A load."},
            {"label": "Max hot spot", "value": "97.5 C", "status": "demo_warn", "note": "Demo IR camera result, not real thermal evidence."},
            {"label": "Ripple", "value": "42 mVpp", "status": "demo_pass", "note": f"Target is <= {spec.output_ripple_mv_pp:g} mVpp."},
        ]
        data = {
            **_base_payload(
                "fake_efficiency_sweep",
                _notice("Power analyzer, electronic load, scope capture, and IR camera logging"),
            ),
            "status": "demo_complete",
            "testConditions": {
                "vinV": 12.0,
                "ambientC": spec.ambient_temp_c,
                "airflow": "still air demo assumption",
                "sampleCount": len(efficiency_points),
            },
            "summaryCards": summary_cards,
            "efficiencyPoints": efficiency_points,
            "instrumentLog": [
                {"instrument": "Power analyzer", "channel": "VIN/VOUT", "status": "demo_stream_recorded"},
                {"instrument": "Electronic load", "channel": "0.3 A to 3.0 A sweep", "status": "demo_stream_recorded"},
                {"instrument": "Oscilloscope", "channel": "Vout ripple and load-step", "status": "demo_capture_recorded"},
                {"instrument": "IR camera", "channel": "MOSFET and inductor hot spots", "status": "demo_snapshot_recorded"},
            ],
            "outputs": [
                {"label": "Efficiency sweep CSV", "path": "fake://lab/data/efficiency_sweep_revA.csv"},
                {"label": "Ripple captures", "path": "fake://lab/scope/vout_ripple_revA.wfm"},
                {"label": "Thermal snapshot", "path": "fake://lab/thermal/ir_snapshot_revA.png"},
            ],
            "realIntegrationPoints": [
                "SCPI power analyzer adapter",
                "Electronic load sweep scheduler",
                "Scope waveform export",
                "Thermal camera or thermocouple logger",
            ],
        }
        return self.complete(
            state,
            SkillRunResult(
                self.module_id,
                self.title,
                "Created fake efficiency sweep, ripple capture, and thermal logging results.",
                data,
                source="fake_lab_adapter",
            ),
        )


class AutoTestReportSkill(AutoEESkill):
    module_id = "test_report"
    title = "Auto Test Report"
    description = "Fake post-prototype report package with evidence and revision actions."

    def run(
        self,
        state: DesignState,
        model_manager: Optional[ModelManager] = None,
        output_dir: Optional[Path] = None,
    ) -> SkillRunResult:
        coding = require_result(state, "embedded_coding_download")
        tuning = require_result(state, "closed_loop_tuning")
        logging = require_result(state, "efficiency_logging")
        report_path = "reports/post_prototype/AutoEE_revA_test_report_demo.pdf"
        sections = [
            {
                "title": "Firmware bring-up",
                "status": "demo_pass",
                "evidence": coding["outputs"][1]["path"],
            },
            {
                "title": "Closed-loop tuning",
                "status": "demo_pass",
                "evidence": tuning["outputs"][0]["path"],
            },
            {
                "title": "Efficiency sweep",
                "status": "demo_pass",
                "evidence": logging["outputs"][0]["path"],
            },
            {
                "title": "Ripple and transient capture",
                "status": "demo_pass",
                "evidence": logging["outputs"][1]["path"],
            },
            {
                "title": "Thermal review",
                "status": "demo_review",
                "evidence": logging["outputs"][2]["path"],
            },
        ]
        revision_actions = [
            "Increase copper near the high-side MOSFET thermal pad before Rev B.",
            "Add Kelvin sense routing option for cleaner current telemetry.",
            "Reserve test pads for SWD, UART telemetry, Vout remote sense, and gate-drive debug.",
            "Run real efficiency sweep at 9 V, 12 V, 24 V, and 36 V input before design signoff.",
        ]
        data = {
            **_base_payload(
                "fake_auto_test_report",
                _notice("Report rendering, evidence attachment, and revision issue creation"),
            ),
            "status": "demo_complete",
            "reportArtifact": f"fake://{report_path}",
            "reportSummary": "Fake Rev A post-prototype report generated from firmware, tuning, efficiency, ripple, transient, and thermal demo data.",
            "overallResult": "demo_review_ready",
            "sections": sections,
            "passFail": [
                {"item": "5 V rail regulation", "target": "+/- 5%", "result": "demo_pass"},
                {"item": "Full-load efficiency", "target": ">= 90%", "result": "demo_pass"},
                {"item": "Output ripple", "target": "<= 50 mVpp", "result": "demo_pass"},
                {"item": "Prototype signoff", "target": "real measured evidence", "result": "not_signoff_demo_only"},
            ],
            "revisionActions": revision_actions,
            "outputs": [
                {"label": "PDF report", "path": f"fake://{report_path}"},
                {"label": "Evidence bundle", "path": "fake://reports/post_prototype/evidence_bundle_revA.zip"},
                {"label": "Revision action list", "path": "fake://reports/post_prototype/revB_actions.json"},
            ],
            "realIntegrationPoints": [
                "Report renderer",
                "Artifact store",
                "Issue tracker or PLM handoff",
                "Signoff approval workflow",
            ],
        }
        return self.complete(
            state,
            SkillRunResult(
                self.module_id,
                self.title,
                "Generated fake post-prototype report and Rev B action list.",
                data,
                source="fake_lab_adapter",
            ),
        )
