"""Independent structural CSV audit; no ODE integration or biological scoring.

Reproduce from repository root with the pinned numerical environment:
  .venv-whitebirch/bin/python experiments/003_whitebirch_intrinsic/results/audit_native_trace.py \
    --workspace data/workspaces/003-whitebirch-gpu-pre-freeze-v7 \
    --frozen-commit 233b068cb7e22663b9ce551806e4a4e573a63872 \
    --output /tmp/whitebirch-runtime-review.json

This preserves the separately written auditor used for runtime_review.json.
It does not import the production validators or either numerical reference.
"""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(workspace, frozen_commit, root):
    records = []
    for trace in sorted((workspace / "traces").glob("rk*_step*.csv")):
        exit_path = trace.with_suffix(".exit.json")
        exit_data = json.loads(exit_path.read_text())
        metadata = exit_data["metadata"]
        steps = metadata["steps_per_ms"]
        parameters = metadata["parameters_float32"]
        with trace.open() as stream:
            rows = list(csv.reader(stream))
        assert rows[0] == ["time_ms", "v_mV", "u_pA", "ref_counter", "curSpike"]
        data = np.array([[float(x) for x in row] for row in rows[1:]])
        assert data.shape == (1200 * steps + 1, 5) and np.isfinite(data).all()
        assert np.allclose(data[:, 0], np.arange(len(data)) / steps, rtol=0, atol=1e-10)
        assert np.array_equal(data[:, 1:3], data[:, 1:3].astype(np.float32).astype(float))
        assert (exit_data["exit_code"] == 0 and exit_data["metadata_matches_freeze"] is True
                and exit_data["frozen_commit"] == frozen_commit and exit_data["failure"] is None)
        errors, resets, suppressed = [], 0, 0
        for index in range(len(data) - 1):
            voltage, recovery, counter = data[index, 1:4]
            next_voltage, next_recovery, next_counter, latch = data[index + 1, 1:]
            last = (index + 1) % steps == 0
            if counter:
                suppressed += 1
                if (next_counter != counter - int(last) or next_recovery != recovery
                        or next_voltage != (parameters["Vmin"] if last else voltage)):
                    errors.append(["refractory", index])
            elif voltage > parameters["Vpeak"]:
                resets += 1
                expected_recovery = float(np.float32(np.float32(recovery) + np.float32(parameters["d"])))
                if (next_voltage != parameters["Vmin"] or next_recovery != expected_recovery
                        or next_counter != (1 if last else 2) or latch != 1):
                    errors.append(["reset", index])
            elif next_counter != 0 or next_voltage < -90:
                errors.append(["smooth", index])
        baseline_error = float(np.max(abs(data[:100 * steps + 1, 1] + 70)))
        holding_error = float(np.max(abs(data[:, 1] + 70))) if metadata["step_current_pA"] == 0 else None
        onset_current = float(parameters["C"] * (data[100 * steps + 1, 1] - data[100 * steps, 1])
                              / metadata["dt_float32_ms"])
        records.append({
            "trace": str(trace.relative_to(root) if trace.is_relative_to(root) else trace), "trace_sha256": digest(trace),
            "native_exit_record_sha256": digest(exit_path), "steps_per_ms": steps,
            "step_current_pA": metadata["step_current_pA"], "shape": list(data.shape),
            "independent_structural_errors": errors, "reset_transitions_audited": resets,
            "refractory_substeps_audited": suppressed, "baseline_max_error_mV": baseline_error,
            "holding_max_error_mV": holding_error,
            "first_pulse_capacitance_times_dVdt_pA": onset_current,
            "first_pulse_dVdt_difference_from_step_pA": onset_current - metadata["step_current_pA"],
            "transition_times_on_observed_grid_ms": [float(data[100 * steps, 0]), float(data[1100 * steps, 0])],
        })
    assert len(records) == 33
    assert {(r["steps_per_ms"], r["step_current_pA"]) for r in records} == {
        (n, current) for n in (20, 40, 80) for current in range(0, 1001, 100)}
    return {
        "kind": "Independent bounded runtime structural review", "frozen_commit": frozen_commit,
        "actual_native_sweeps": 33, "all_native_exit_zero_and_metadata_verified": True,
        "trace_completeness_clock_float32_pass": True,
        "independent_reset_refractory_pass": all(not r["independent_structural_errors"] for r in records),
        "all_baselines_exact_minus70": all(r["baseline_max_error_mV"] == 0 for r in records),
        "all_holding_only_traces_exact_minus70": all(r["holding_max_error_mV"] == 0 for r in records
                                                    if r["step_current_pA"] == 0),
        "records": records,
        "method": "Separately written CSV audit of every reset/refractory transition, float32 state roundtrip and grid. No production validator, ODE integration, reference output or biological target score reused in this final audit. Native exit records provide applied-current metadata; source-defined runNetwork phase boundaries match trace grid. Onset finite difference is descriptive engineering telemetry, not a preregistered acceptance gate.",
        "limitations": [
            "No direct external-current channel recorded; transition-current identity rests on frozen harness source, exact native configuration and phase durations, with first-onset voltage finite-difference check as supporting evidence.",
            "Structural success is not independent high-accuracy integration validation; tightened reference and timestep comparison gates remain pending.",
            "No biological agreement assessment performed.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--frozen-commit", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    result = audit(args.workspace.resolve(), args.frozen_commit, root)
    result["auditor_source"] = str(Path(__file__).resolve().relative_to(root))
    result["auditor_sha256"] = digest(__file__)
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
