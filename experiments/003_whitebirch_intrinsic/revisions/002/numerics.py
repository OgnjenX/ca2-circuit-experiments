"""Predeclared GPU-trace numerical verification; contains no biological scoring.

Execution belongs to the gated frozen driver. Importing this module performs
no simulation. Raw references are written only to the supplied fresh workspace.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

TIME_LIMIT_MS = 0.05
RESET_U_LIMIT_PA = 0.01
DT_STEPS = (20, 40, 80)
CURRENTS = tuple(range(0, 1001, 100))
REFERENCE_CONTROLS = ((1e-9, 1e-10, 0.5), (1e-11, 1e-12, 0.1))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def phase_counts(times):
    return {"pre": sum(0 <= t < 100 for t in times),
            "pulse": sum(100 <= t < 1100 for t in times),
            "post": sum(1100 <= t <= 1200 for t in times)}


def detector_audit(times):
    """Count event equivalents with >=6 ms separation, without waveform claims."""
    accepted = []
    for t in times:
        if not accepted or t - accepted[-1] >= 6.0:
            accepted.append(t)
    isi = [b-a for a, b in zip(times, times[1:])]
    return {"raw_counts": phase_counts(times), "compatible_counts": phase_counts(accepted),
            "pulse_inclusive_count": sum(100 <= t <= 1100 for t in times),
            "nearest_phase_boundaries": {str(boundary):
                ({"event_time_ms": min(times, key=lambda t: abs(t-boundary)),
                  "distance_ms": min(abs(t-boundary) for t in times)} if times else None)
                for boundary in (100, 1100, 1200)},
            "windows": "pre [0,100), primary pulse [100,1100), post [1100,1200] (recording end closed)",
            "whole_trace_raw": len(times), "whole_trace_compatible": len(accepted),
            "minimum_ISI_ms": min(isi) if isi else None,
            "ISIs_below_6ms": [x for x in isi if x < 6.0],
            "amplitude_equivalent_mV": None,
            "pulse_endpoint_brackets": []}


def validate_metadata(metadata):
    required = ("parameters_float32", "holding_float32_pA", "pulse_float32_pA",
                "initial_u_float32_pA", "steps_per_ms", "step_current_pA")
    for key in required:
        if key not in metadata:
            raise ValueError(f"Native metadata missing {key}")
    if metadata.get("mode") != "GPU_MODE":
        raise ValueError("Actual native GPU_MODE metadata required")
    if set(metadata["parameters_float32"]) != {"C", "k", "Vr", "Vt", "a", "b", "Vpeak", "Vmin", "d"}:
        raise ValueError("Unexpected native parameter key set")
    for key, allowed in (("steps_per_ms", DT_STEPS), ("step_current_pA", CURRENTS)):
        value = metadata[key]
        if isinstance(value, bool) or not isinstance(value, int) or value not in allowed:
            raise ValueError(f"Invalid native integer grid metadata: {key}")
    if "dt_ms" in metadata and metadata["dt_ms"] != 1/metadata["steps_per_ms"]:
        raise ValueError("Native timestep metadata inconsistent with substep clock")
    if "dt_float32_ms" in metadata and metadata["dt_float32_ms"] != float(np.float32(1/metadata["steps_per_ms"])):
        raise ValueError("Actual float32 timestep differs from substep clock")
    if "refractory_period" in metadata and metadata["refractory_period"] != 1:
        raise ValueError("Native refractory period differs from archived value")
    for key in ("Izh_ref", "hardcoded_Izh_ref", "refractory_constant"):
        if key in metadata and metadata[key] != 1:
            raise ValueError("Native refractory constant differs from archived value")
    for value in (*metadata["parameters_float32"].values(),
                  metadata["holding_float32_pA"], metadata["pulse_float32_pA"],
                  metadata["initial_u_float32_pA"]):
        if not math.isfinite(value) or float(np.float32(value)) != value:
            raise ValueError("Metadata does not roundtrip to actual float32")
    expected = float(np.float32(np.float32(metadata["holding_float32_pA"])
                                + np.float32(metadata["step_current_pA"])))
    if expected != metadata["pulse_float32_pA"]:
        raise ValueError("Pulse current inconsistent with native float32 addition")


def validate_trace(path, metadata):
    """Validate complete END-substep observations and extract structural events.

    Reset/detection time is the span START; smooth crossing estimates use
    interpolation between observed endpoints and retain the entire bracket.
    curSpike is a millisecond latch, so it is never counted as independent APs.
    """
    validate_metadata(metadata)
    steps = int(metadata["steps_per_ms"])
    if steps not in DT_STEPS:
        raise ValueError("Unregistered timestep")
    with Path(path).open() as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["time_ms", "v_mV", "u_pA", "ref_counter", "curSpike"]:
            raise ValueError("Unexpected trace columns")
        rows = [[float(r[k]) for k in reader.fieldnames] for r in reader]
    data = np.asarray(rows, dtype=float)
    if data.shape != (1200*steps+1, 5) or not np.isfinite(data).all():
        raise ValueError("Incomplete or nonfinite native trace")
    if not np.array_equal(data[:, 1:3], data[:, 1:3].astype(np.float32).astype(float)):
        raise ValueError("Native state trace does not roundtrip to float32")
    if not np.allclose(data[:, 0], np.arange(len(data))/steps, atol=1e-10, rtol=0):
        raise ValueError("Invalid substep clock")
    if not np.all(data[:, 3] == np.floor(data[:, 3])) or not np.isin(data[:, 3], [0, 1, 2]).all():
        raise ValueError("Invalid refractory counters")
    if not np.isin(data[:, 4], [0, 1]).all():
        raise ValueError("Invalid curSpike latch")
    if not np.array_equal(data[0], [0, -70, metadata["initial_u_float32_pA"], 0, 0]):
        raise ValueError("Initial state differs from native roundtrip metadata")
    p = metadata["parameters_float32"]
    events, crossings, errors, clamps = [], [], [], []
    pending = None
    for index, (previous, after) in enumerate(zip(data, data[1:])):
        start, end = previous[0], after[0]
        last = (index+1) % steps == 0
        if previous[3] > 0:
            expected_counter = previous[3] - int(last)
            expected_v = p["Vmin"] if last else previous[1]
            if after[3] != expected_counter or after[1] != expected_v or after[2] != previous[2]:
                errors.append({"kind": "refractory_freeze", "clock_index": index})
        elif previous[1] > p["Vpeak"]:
            expected_u = float(np.float32(np.float32(previous[2]) + np.float32(p["d"])))
            if after[1] != p["Vmin"] or after[2] != expected_u or after[3] != (1 if last else 2) or after[4] != 1:
                errors.append({"kind": "reset_state", "clock_index": index})
            events.append({"time_ms": start, "clock_index": index,
                           "crossing_time_ms": pending, "v_before": previous[1],
                           "u_before": previous[2], "v_after": after[1], "u_after": after[2],
                           "refractory_counter_after": int(after[3])})
            pending = None
        else:
            if after[3] != 0:
                errors.append({"kind": "unexpected_counter", "clock_index": index})
            if after[1] < -90.0:
                errors.append({"kind": "voltage_floor_violation", "clock_index": index})
            if after[1] == -90.0:
                clamps.append(end)
            if previous[1] <= p["Vpeak"] < after[1]:
                fraction = (p["Vpeak"]-previous[1])/(after[1]-previous[1])
                pending = start + fraction*(end-start)
                crossings.append({"time_ms": pending, "bracket_ms": [start, end],
                                  "clock_index": index})
    crossing_times = [r["time_ms"] for r in crossings]
    detection_times = [r["time_ms"] for r in events]
    ca, da = detector_audit(crossing_times), detector_audit(detection_times)
    ca["amplitude_equivalent_mV"] = p["Vpeak"]+70.0
    da["amplitude_equivalent_mV"] = p["Vpeak"]+70.0
    ca["pulse_endpoint_brackets"] = [c["bracket_ms"] for c in crossings
                                      if any(c["bracket_ms"][0] <= x <= c["bracket_ms"][1]
                                             for x in (100, 1100))]
    holding = metadata["step_current_pA"] == 0
    baseline_error = float(np.max(np.abs(data[:100*steps+1, 1]+70)))
    hold_error = float(np.max(np.abs(data[:, 1]+70))) if holding else None
    holding_pass = baseline_error <= .002 and (not holding or (not crossings and not events and hold_error <= .002))
    unresolved = (ca["raw_counts"] != da["raw_counts"] or ca["raw_counts"] != ca["compatible_counts"]
                  or da["raw_counts"] != da["compatible_counts"] or bool(ca["pulse_endpoint_brackets"])
                  or ca["whole_trace_raw"] != ca["raw_counts"]["pulse"]
                  or da["whole_trace_raw"] != da["raw_counts"]["pulse"])
    return {"path": str(path), "sha256": sha256(path), "metadata": metadata,
            "events": events, "crossings": crossings, "reset_rule_errors": errors,
            "voltage_floor_clamps_ms": clamps, "crossing_audit": ca, "detection_audit": da,
            "baseline_max_error_mV": baseline_error, "holding_max_error_mV": hold_error,
            "holding_check_pass": holding_pass, "comparability_unresolved": unresolved,
            "undetected_final_crossing_time_ms": pending,
            "trace_rules_pass": not errors and holding_pass}


def compare_events(first, second, crossing_key="crossings", reset_u=True):
    a, b = first[crossing_key], second[crossing_key]
    same_count = len(a) == len(b)
    times_a, times_b = [x["time_ms"] for x in a], [x["time_ms"] for x in b]
    ordered = all(x < y for x, y in zip(times_a, times_a[1:])) and all(x < y for x, y in zip(times_b, times_b[1:]))
    stable = same_count and phase_counts(times_a) == phase_counts(times_b) and ordered
    error = max((abs(x-y) for x, y in zip(times_a, times_b)), default=0) if same_count else None
    reset_error = None
    reset_stable = len(first["events"]) == len(second["events"])
    if reset_u and reset_stable:
        reset_error = max((abs(a["u_before"]-b["u_before"])
                           for a, b in zip(first["events"], second["events"])), default=0)
    return {"stable_counts_order_and_phases": stable, "max_time_error_ms": error,
            "max_reset_u_before_error_pA": reset_error,
            "pass": stable and error is not None and error < TIME_LIMIT_MS
                    and (not reset_u or (reset_stable and reset_error < RESET_U_LIMIT_PA))}


def validate_clock_reference(reference):
    p = reference["parameters"]
    errors = []
    steps = reference["substeps_per_ms"]
    for event in reference["events"]:
        last = (event["clock_index"]+1) % steps == 0
        if (not event["v_before"] > p["Vpeak"] or event["v_after"] != p["Vmin"]
                or abs(event["u_after"]-event["u_before"]-p["d"]) >= 1e-7
                or event["refractory_counter_after"] != (1 if last else 2)
                or event["last_iteration"] != last):
            errors.append({"kind": "reference_reset_invariant", "clock_index": event["clock_index"]})
    boundary = reference["boundary_states"]
    baseline_error = max(abs(s["v_mV"]+70) for s in boundary if s["time_ms"] <= 100)
    holding = reference["step_current_pA"] == 0
    hold_error = max(abs(s["v_mV"]+70) for s in boundary) if holding else None
    hold_pass = baseline_error <= .002 and (not holding or (not reference["events"]
                    and not reference["crossings"] and hold_error <= .002))
    return {"reset_invariant_errors": errors, "holding_check_pass": hold_pass,
            "baseline_boundary_error_mV": baseline_error, "holding_boundary_error_mV": hold_error,
            "pass": not errors and hold_pass}


def validate_records(records):
    """Aggregate same-grid checks and separate production timestep refinement."""
    expected = {(steps, current) for steps in DT_STEPS for current in CURRENTS}
    actual = {(r["metadata"]["steps_per_ms"], r["metadata"]["step_current_pA"]) for r in records}
    if actual != expected or len(records) != len(expected):
        raise ValueError("Assay records incomplete or duplicated")
    template = records[0]["metadata"]
    consistent_fields = ("parameters_float32", "holding_float32_pA", "initial_u_float32_pA",
                         "library_sha256")
    for record in records:
        if any(record["metadata"].get(key) != template.get(key) for key in consistent_fields):
            raise ValueError("Actual native configuration changed between assay records")
    refinements = []
    lookup = {(r["metadata"]["steps_per_ms"], r["metadata"]["step_current_pA"]): r for r in records}
    for current in CURRENTS:
        for coarse, fine in ((20, 40), (40, 80), (20, 80)):
            a, b = lookup[coarse, current], lookup[fine, current]
            crossing = compare_events(a, b, reset_u=False)
            detection = compare_events(a, b, crossing_key="events", reset_u=False)
            refinements.append({"current_pA": current, "steps_per_ms": [coarse, fine],
                                "crossings": crossing, "detections": detection,
                                "pass": crossing["pass"] and detection["pass"]})
    passed = all(r["trace_rules_pass"] and r["same_grid_crossings"]["pass"]
                 and r["same_grid_detections"]["pass"] and r["reference_refinement_crossings"]["pass"]
                 and r["reference_refinement_detections"]["pass"]
                 and r["reference_reset_audit"]["pass"] for r in records)
    return {"passed": passed and all(x["pass"] for x in refinements),
            "production_timestep_refinements": refinements,
            "comparability_unresolved": any(r["comparability_unresolved"] for r in records),
            "criteria": {"event_time_error_strictly_below_ms": TIME_LIMIT_MS,
                         "same_grid_reset_u_error_strictly_below_pA": RESET_U_LIMIT_PA,
                         "holding_voltage_error_at_most_mV": .002},
            "interpretation": "Engineering verification only; failure blocks biological discrepancy interpretation."}


def metadata_for(workspace, trace, frozen_commit, pins, checker=None):
    stdout, stderr = trace.with_suffix(".stdout"), trace.with_suffix(".stderr")
    exit_path = trace.with_suffix(".exit.json")
    if not all(path.is_file() for path in (stdout, stderr, exit_path)):
        raise ValueError("Every native trace requires adjacent stdout, stderr and exit record")
    match = re.fullmatch(r"rk(20|40|80)_step(\d+)", trace.stem)
    if not match:
        raise ValueError("Unrecognized trace name")
    steps, current = map(int, match.groups())
    exit_record = json.loads(exit_path.read_text())
    if (type(exit_record.get("exit_code")) is not int or exit_record["exit_code"] != 0
            or exit_record.get("metadata_matches_freeze") is not True
            or exit_record.get("frozen_commit") != frozen_commit or exit_record.get("failure") is not None):
        raise ValueError("Native exit/configuration/frozen-commit record failed")
    if checker is None:
        driver = Path(__file__).resolve().parents[2]/"preparation"/"build_driver.py"
        spec = importlib.util.spec_from_file_location("whitebirch_build_driver", driver)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        checker = module.check_metadata
    metadata = checker(stdout.read_text(), steps, current, pins)
    if exit_record.get("metadata") != metadata:
        raise ValueError("Native exit metadata differs from actual stdout")
    return metadata, stdout


def verify_frozen_inputs(frozen_commit):
    """Require unchanged committed frozen inputs and authoritative stage gate."""
    here = Path(__file__).resolve().parent
    root = here.parents[3]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if not frozen_commit:
        raise ValueError("An explicit preregistration frozen commit is required")
    frozen_commit = subprocess.check_output(["git", "rev-parse", frozen_commit], cwd=root, text=True).strip()
    subprocess.run(["git", "merge-base", "--is-ancestor", frozen_commit, head], cwd=root, check=True)
    inputs = [here/name for name in ("numerics.py", "reference_carlsim.py", "reference_immediate.py",
                                     "protocol.json", "preregistration_manifest.json", "verify_stages.py")]
    for source in inputs:
        relative = source.relative_to(root).as_posix()
        committed = subprocess.check_output(["git", "show", f"{frozen_commit}:{relative}"], cwd=root)
        if committed != source.read_bytes():
            raise ValueError(f"Uncommitted numerical input: {relative}")
    subprocess.run([sys.executable, str(here/"verify_stages.py"), "--require-numerical-ready"],
                   cwd=root, check=True)
    return frozen_commit


def actual_parameters(metadata):
    parameters = dict(metadata["parameters_float32"])
    parameters.update(initial_state=[-70, metadata["initial_u_float32_pA"]],
                      holding_current_pA=metadata["holding_float32_pA"],
                      pulse_current_pA=metadata["pulse_float32_pA"])
    return parameters


def immediate_diagnostic(records, output, frozen_commit):
    from reference_immediate import simulate
    result = {"passed": False, "records": [], "rawhashes": {}, "frozen_commit": frozen_commit,
              "scope": "Separate immediate-reset diagnostic; no CARLsim refractory clock and no biological scoring."}
    try:
        finest = {r["metadata"]["step_current_pA"]: r for r in records
                  if r["metadata"]["steps_per_ms"] == 80}
        if set(finest) != set(CURRENTS):
            raise ValueError("Immediate diagnostic requires all finest-grid native configurations")
        for current in CURRENTS:
            metadata = finest[current]["metadata"]
            references, paths = [], []
            for label, controls in zip(("loose", "tight"), REFERENCE_CONTROLS):
                reference = simulate(actual_parameters(metadata), current, *controls)
                path = output/f"immediate_step{current}_{label}.json"
                path.write_text(json.dumps(reference, indent=2)+"\n")
                result["rawhashes"][str(path)] = sha256(path)
                references.append(reference)
                paths.append(str(path))
            loose, tight = references
            # The immediate reference represents localized crossings as events.
            refined = compare_events(loose, tight, "events")
            checks = []
            for reference in references:
                p = reference["parameters"]
                reset_pass = all(abs(e["v_before"]-p["Vpeak"]) < 1e-7
                                 and e["v_after"] == p["Vmin"]
                                 and abs(e["u_after"]-e["u_before"]-p["d"]) < 1e-9
                                 for e in reference["events"])
                boundary_hold_error = max(abs(b["v_mV"]+70) for b in reference["boundary_states"])
                baseline_error = max(abs(b["v_mV"]+70) for b in reference["boundary_states"] if b["time_ms"] <= 100)
                hold_pass = baseline_error <= .002 and (current != 0 or (not reference["events"] and boundary_hold_error <= .002))
                checks.append({"reset_states_pass": reset_pass, "holding_check_pass": hold_pass,
                               "baseline_boundary_max_error_mV": baseline_error,
                               "holding_boundary_max_error_mV": boundary_hold_error if current == 0 else None,
                               "holding_sampling": "All returned phase-boundary states; event absence also required.",
                               "audit": detector_audit([e["time_ms"] for e in reference["events"]])})
            passed = refined["pass"] and all(c["reset_states_pass"] and c["holding_check_pass"] for c in checks)
            result["records"].append({"step_current_pA": current, "events": tight["events"],
                                      "refinement_pass": passed, "refinement": refined,
                                      "loose_metrics": checks[0], "tight_metrics": checks[1],
                                      "rawpaths": paths})
            print(f"Immediate diagnostic step {current} pA: both reference refinements complete; pass={passed}", flush=True)
        result["passed"] = all(r["refinement_pass"] for r in result["records"])
    except Exception as error:
        result.update(incomplete_or_invalid=True, failure=f"{type(error).__name__}: {error}")
    (output/"immediate_diagnostic.json").write_text(json.dumps(result, indent=2)+"\n")
    return result


def run(workspace, output, frozen_commit):
    frozen_commit = verify_frozen_inputs(frozen_commit)
    # Deliberately deferred import: no integration on module import or trace-only audit.
    from reference_carlsim import simulate
    output.mkdir(parents=True, exist_ok=False)
    records, raw_hashes = [], {}
    try:
        manifest = json.loads((Path(__file__).resolve().parent/"preregistration_manifest.json").read_text())
        traces = sorted(workspace.rglob("rk*_step*.csv"))
        if len(traces) != len(DT_STEPS)*len(CURRENTS):
            raise ValueError("Expected all 33 native traces before numerical validation")
        for trace in traces:
            raw_hashes[str(trace)] = sha256(trace)
            for suffix in (".stdout", ".stderr", ".exit.json"):
                sidecar = trace.with_suffix(suffix)
                if sidecar.exists(): raw_hashes[str(sidecar)] = sha256(sidecar)
            metadata, stdout = metadata_for(workspace, trace, frozen_commit, manifest["runtime_pins"])
            record = validate_trace(trace, metadata)
            parameters = actual_parameters(metadata)
            references = []
            for label, (rtol, atol, max_step) in zip(("loose", "tight"), REFERENCE_CONTROLS):
                reference = simulate(parameters, metadata["step_current_pA"],
                                     1/metadata["steps_per_ms"], rtol, atol, max_step)
                path = output / f"{trace.stem}_reference_{label}.json"
                path.write_text(json.dumps(reference, indent=2)+"\n")
                raw_hashes[str(path)] = sha256(path)
                references.append(reference)
            loose, tight = references
            reference_checks = [validate_clock_reference(ref) for ref in references]
            record["reference_reset_audit"] = {"pass": all(c["pass"] for c in reference_checks),
                                               "loose": reference_checks[0], "tight": reference_checks[1]}
            record["reference_refinement_crossings"] = compare_events(loose, tight)
            record["reference_refinement_detections"] = compare_events(loose, tight, "events")
            record["same_grid_crossings"] = compare_events(record, tight)
            record["same_grid_detections"] = compare_events(record, tight, "events")
            record["reference_raw_files"] = [f"{trace.stem}_reference_{x}.json" for x in ("loose", "tight")]
            records.append(record)
            print(f"{trace.stem}: both clock-reference refinements complete", flush=True)
        result = validate_records(records)
    except Exception as error:
        result = {"passed": False, "incomplete_or_invalid": True,
                  "failure": f"{type(error).__name__}: {error}",
                  "interpretation": "No biological interpretation permitted."}
    result.update(records=records, raw_file_sha256=raw_hashes, frozen_commit=frozen_commit,
                  controls={"reference": REFERENCE_CONTROLS, "production_steps_per_ms": DT_STEPS},
                  initial_state_note="Native actual float32 parameters, u, holding and pulse current are independently integrated in float64; no exact-equilibrium assumption after rounding.")
    (output/"numerical_checks.json").write_text(json.dumps(result, indent=2)+"\n")
    diagnostic = immediate_diagnostic(records, output, frozen_commit)
    result["immediate_diagnostic_passed"] = diagnostic["passed"]
    result["immediate_diagnostic_sha256"] = sha256(output/"immediate_diagnostic.json")
    (output/"numerical_checks.json").write_text(json.dumps(result, indent=2)+"\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--frozen-commit", required=True)
    args = parser.parse_args()
    result = run(args.workspace.resolve(), args.output.resolve(), args.frozen_commit)
    print(json.dumps({"passed": result["passed"], "failure": result.get("failure"),
                      "output": str(args.output)}, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
