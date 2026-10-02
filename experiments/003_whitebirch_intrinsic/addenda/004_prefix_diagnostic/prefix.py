"""Post hoc, single-condition pre-reset numerical precision diagnostic.

Importing performs no simulation. Five finite, predefined integrations stop at
858.4875 ms and never implement resets. Native GPU output is read, never rerun.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

HERE = Path(__file__).resolve().parent
ASSAY = HERE.parents[1]
ROOT = ASSAY.parents[1]
END_MS = 858.4875
SUBSTEPS = 80
FIRST_RESET_MS = 858.5
DRIFT = 1e-5
CONTROLS = ((1e-9, 1e-10, .5), (1e-11, 1e-12, .1))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frozen_inputs(commit, trace):
    commit = subprocess.check_output(["git", "rev-parse", commit], cwd=ROOT, text=True).strip()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    subprocess.run(["git", "merge-base", "--is-ancestor", commit, head], cwd=ROOT, check=True)
    manifest_path = HERE/"preregistration_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if "addenda/004_prefix_diagnostic/prefix.py" not in manifest["sha256"]:
        raise ValueError("Diagnostic code must be pinned")
    for relative in set(manifest["sha256"]) | {"addenda/004_prefix_diagnostic/preregistration_manifest.json"}:
        path = ASSAY/relative
        saved = subprocess.check_output(["git", "show", f"{commit}:{path.relative_to(ROOT)}"], cwd=ROOT)
        if saved != path.read_bytes() or (relative in manifest["sha256"] and digest(path) != manifest["sha256"][relative]):
            raise ValueError(f"Diagnostic frozen source changed: {relative}")
    paths = [trace, trace.with_suffix(".stdout"), trace.with_suffix(".stderr"), trace.with_suffix(".exit.json")]
    if set(manifest["native_sha256"]) != {path.name for path in paths}:
        raise ValueError("Diagnostic manifest must pin the four exact native inputs")
    for path in paths:
        if digest(path) != manifest["native_sha256"][path.name]:
            raise ValueError(f"Native source checksum differs: {path}")
    exit_record = json.loads(paths[3].read_text())
    if (exit_record.get("exit_code") != 0 or exit_record.get("metadata_matches_freeze") is not True
            or exit_record.get("frozen_commit") != manifest["source_freeze_commit"]
            or exit_record.get("failure") is not None):
        raise ValueError("Original native exit/configuration record failed")
    source_manifest = json.loads((ASSAY/"revisions/002/preregistration_manifest.json").read_text())
    original_manifest = subprocess.check_output(["git", "show",
        f'{manifest["source_freeze_commit"]}:{(ASSAY/"revisions/002/preregistration_manifest.json").relative_to(ROOT)}'], cwd=ROOT)
    if original_manifest != (ASSAY/"revisions/002/preregistration_manifest.json").read_bytes():
        raise ValueError("Original preregistration manifest changed")
    for relative, sha in source_manifest["sha256"].items():
        if digest(ASSAY/relative) != sha:
            raise ValueError(f"Original frozen source changed: {relative}")
    spec = importlib.util.spec_from_file_location("prefix_metadata_driver", ASSAY/"preparation/build_driver.py")
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    metadata = driver.check_metadata(paths[1].read_text(), SUBSTEPS, 100, source_manifest["runtime_pins"])
    if exit_record.get("metadata") != metadata:
        raise ValueError("Native stdout and exit metadata differ")
    return commit, manifest, metadata


def rhs(values, p, current, inverse_c):
    v, u = values
    return np.array([(p["k"]*(v-p["Vr"])*(v-p["Vt"])-u+current)*inverse_c,
                     p["a"]*(p["b"]*(v-p["Vr"])-u)], dtype=np.float64)


def rk4_double(times, initial, p, holding, pulse, inverse_c, integration_dt, one_sixth=1/6):
    state = np.array(initial, dtype=np.float64)
    output = [state.copy()]
    for start in times[:-1]:
        current = holding if start < 100 else pulse
        a = integration_dt*rhs(state, p, current, inverse_c)
        b = integration_dt*rhs(state+a/2, p, current, inverse_c)
        c = integration_dt*rhs(state+b/2, p, current, inverse_c)
        d = integration_dt*rhs(state+c, p, current, inverse_c)
        state = state+one_sixth*(a+2*b+2*c+d)
        output.append(state.copy())
    return np.asarray(output)


def rk4_float32(times, initial, parameters, holding, pulse):
    """Explicit scalar rounding after each operation; no fused multiply-add."""
    f = np.float32
    p = {name: f(value) for name, value in parameters.items()}
    inverse_c, dt = f(f(1)/p["C"]), f(1/SUBSTEPS)
    add = lambda x, y: f(f(x)+f(y))
    sub = lambda x, y: f(f(x)-f(y))
    mul = lambda x, y: f(f(x)*f(y))
    div = lambda x, y: f(f(x)/f(y))

    def increment(v, u, current):
        numerator = add(sub(mul(mul(p["k"], sub(v, p["Vr"])), sub(v, p["Vt"])), u), current)
        kv = mul(mul(numerator, inverse_c), dt)
        ku = mul(mul(p["a"], sub(mul(p["b"], sub(v, p["Vr"])), u)), dt)
        return kv, ku

    v, u = map(f, initial)
    output = [[float(v), float(u)]]
    for start in times[:-1]:
        current = f(holding if start < 100 else pulse)
        av, au = increment(v, u, current)
        bv, bu = increment(add(v, div(av, 2)), add(u, div(au, 2)), current)
        cv, cu = increment(add(v, div(bv, 2)), add(u, div(bu, 2)), current)
        dv, du = increment(add(v, cv), add(u, cu), current)
        weight = lambda a, b, c, d: mul(div(1, 6), add(add(add(a, mul(2, b)), mul(2, c)), d))
        v, u = add(v, weight(av, bv, cv, dv)), add(u, weight(au, bu, cu, du))
        output.append([float(v), float(u)])
    return np.asarray(output)


def dop853(times, initial, p, holding, pulse, controls):
    rtol, atol, max_step = controls
    state = np.array(initial, dtype=np.float64)
    output = np.empty((len(times), 2))
    for start, end, current in ((0., 100., holding), (100., END_MS, pulse)):
        solution = solve_ivp(lambda _t, values: rhs(values, p, current, 1/p["C"]),
                             (start, end), state, method="DOP853", dense_output=True,
                             rtol=rtol, atol=atol, max_step=max_step)
        if not solution.success:
            raise RuntimeError(f"Smooth reference integration failed: {solution.message}")
        mask = (times >= start) & (times <= end)
        output[mask] = solution.sol(times[mask]).T
        state = solution.y[:, -1].copy()
    return output


def telemetry(times, first, second):
    delta = first-second
    result = {}
    for index, name in enumerate(("voltage_mV", "recovery_pA")):
        exceeded = np.flatnonzero(np.abs(delta[:, index]) > DRIFT)
        first_index = int(exceeded[0]) if len(exceeded) else None
        result[name] = {"max_abs": float(np.max(np.abs(delta[:, index]))),
                        "rms": float(np.sqrt(np.mean(delta[:, index]**2))),
                        "signed_endpoint_difference": float(delta[-1, index]),
                        "first_exceedance_threshold": DRIFT,
                        "first_exceedance_time_ms": float(times[first_index]) if first_index is not None else None,
                        "first_exceedance_signed_difference": float(delta[first_index, index]) if first_index is not None else None}
    return result


def crossing_bracket(times, states, peak):
    indices = np.flatnonzero((states[:-1, 0] <= peak) & (states[1:, 0] > peak))
    if not len(indices):
        return None
    index = int(indices[0])
    fraction = (peak-states[index, 0])/(states[index+1, 0]-states[index, 0])
    return {"bracket_ms": [float(times[index]), float(times[index+1])],
            "linear_interpolation_ms": float(times[index]+fraction*(times[index+1]-times[index]))}


def run(trace, output, frozen_commit):
    commit, manifest, metadata = frozen_inputs(frozen_commit, trace)
    if output.exists():
        raise ValueError("Prefix diagnostic output must be fresh")
    with trace.open() as stream:
        rows = list(csv.DictReader(stream))
    data = np.array([[float(row[key]) for key in ("time_ms", "v_mV", "u_pA", "ref_counter", "curSpike")]
                     for row in rows])
    if data.shape != (1200*SUBSTEPS+1, 5) or not np.isfinite(data).all():
        raise ValueError("Original native trace incomplete/nonfinite")
    if not np.allclose(data[:, 0], np.arange(len(data))/SUBSTEPS, rtol=0, atol=1e-10):
        raise ValueError("Original native clock invalid")
    count = round(END_MS*SUBSTEPS)+1
    times, native = data[:count, 0], data[:count, 1:3]
    p = metadata["parameters_float32"]
    initial = [-70., metadata["initial_u_float32_pA"]]
    if not np.array_equal(native[0], initial) or np.any(data[:count, 3:5] != 0):
        raise ValueError("Prefix contains reset/refractory/AP latch or incorrect initialization")
    reset_indices = np.flatnonzero((data[:-1, 1] > p["Vpeak"]) & (data[:-1, 3] == 0))
    if not len(reset_indices) or abs(data[int(reset_indices[0])+1, 0]-FIRST_RESET_MS) > 1e-10:
        raise ValueError("Native first-reset boundary differs from declared stopping rule")
    before_reset, after_reset = data[int(reset_indices[0])], data[int(reset_indices[0])+1]
    reset_u = float(np.float32(np.float32(before_reset[2])+np.float32(p["d"])))
    if after_reset[1] != p["Vmin"] or after_reset[2] != reset_u or after_reset[4] != 1:
        raise ValueError("Native declared first reset lacks reset state/AP signal")
    hold, pulse = metadata["holding_float32_pA"], metadata["pulse_float32_pA"]
    matched_inverse = float(np.float32(np.float32(1)/np.float32(p["C"])))
    matched_dt = float(np.float32(1/SUBSTEPS))
    matched_one_sixth = float(np.float32(np.float32(1)/np.float32(6)))
    methods = {}
    for label, controls in zip(("dop853_loose", "dop853_tight"), CONTROLS):
        methods[label] = dop853(times, initial, p, hold, pulse, controls)
    methods["rk4_float64_exact_coefficients"] = rk4_double(times, initial, p, hold, pulse, 1/p["C"], 1/SUBSTEPS)
    methods["rk4_float64_matched_float32_coefficients"] = rk4_double(times, initial, p, hold, pulse, matched_inverse, matched_dt, matched_one_sixth)
    methods["rk4_float32_explicit_no_fma"] = rk4_float32(times, initial, p, hold, pulse)
    if any(not np.isfinite(values).all() for values in methods.values()):
        raise ValueError("Prefix diagnostic generated nonfinite states")
    output.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for label, states in methods.items():
        path = output/f"{label}.csv"
        with path.open("w") as stream:
            writer = csv.writer(stream)
            writer.writerow(["time_ms", "v_mV", "u_pA"])
            writer.writerows(zip(times, states[:, 0], states[:, 1]))
        hashes[path.name] = digest(path)
    brackets = {label: crossing_bracket(times, states, p["Vpeak"]) for label, states in {"native": native, **methods}.items()}
    common_end = min([END_MS]+[bracket["bracket_ms"][0] for bracket in brackets.values() if bracket is not None])
    mask = times <= common_end
    comparisons = {f"native_vs_{label}": telemetry(times[mask], native[mask], states[mask]) for label, states in methods.items()}
    comparisons["dop853_tolerance_refinement"] = telemetry(times[mask], methods["dop853_loose"][mask], methods["dop853_tight"][mask])
    comparisons["rk4_float64_exact_vs_dop853_tight"] = telemetry(times[mask], methods["rk4_float64_exact_coefficients"][mask], methods["dop853_tight"][mask])
    comparisons["rk4_float64_matched_vs_dop853_tight"] = telemetry(times[mask], methods["rk4_float64_matched_float32_coefficients"][mask], methods["dop853_tight"][mask])
    comparisons["rk4_coefficient_rounding"] = telemetry(times[mask], methods["rk4_float64_exact_coefficients"][mask], methods["rk4_float64_matched_float32_coefficients"][mask])
    comparisons["rk4_float32_operation_rounding"] = telemetry(times[mask], methods["rk4_float32_explicit_no_fma"][mask], methods["rk4_float64_matched_float32_coefficients"][mask])
    checkpoint_times = [0., 100., 100.0125, 200., 400., 600., 800., 858.475, 858.4875]
    checkpoints = {label: [{"time_ms": time, "v_mV": float(states[round(time*SUBSTEPS), 0]),
                           "u_pA": float(states[round(time*SUBSTEPS), 1]),
                           "within_common_prethreshold_prefix": time <= common_end}
                          for time in checkpoint_times] for label, states in {"native": native, **methods}.items()}
    record = {"frozen_diagnostic_commit": commit, "source_freeze_commit": manifest["source_freeze_commit"],
              "native_input_sha256": manifest["native_sha256"], "state_csv_sha256": hashes,
              "window_ms": [0., END_MS], "sample_count": len(times), "native_first_reset_end_ms": FIRST_RESET_MS,
              "native_first_reset_detection_ms": float(data[int(reset_indices[0]), 0]),
              "valid_comparison_end_ms": common_end, "first_threshold_brackets": brackets,
              "reference_reliable_for_drift_attribution": all(component["max_abs"] <= 1e-7
                  for component in comparisons["dop853_tolerance_refinement"].values()),
              "reference_attribution_refinement_threshold": {"voltage_mV": 1e-7, "recovery_pA": 1e-7},
              "checkpoints": checkpoints,
              "post_crossing_note": "Saved no-reset smooth extensions beyond each method's crossing are not claimed faithful to the resetting GPU model; telemetry uses only the common prethreshold prefix.",
              "actual_native_metadata": metadata, "controls": CONTROLS,
              "coefficient_handling": {"exact_inverse_C": 1/p["C"], "matched_float32_inverse_C": matched_inverse,
                                       "exact_dt_ms": 1/SUBSTEPS, "matched_float32_dt_ms": matched_dt,
                                       "exact_one_sixth": 1/6, "matched_float32_one_sixth": matched_one_sixth,
                                       "matched_variant_note": "Float64 matched variant jointly changes inverseC, dt and one-sixth coefficients; no variant selection.",
                                       "inverse_C_note": "GPU kernel computes float reciprocal; inferred from pinned actual C, not directly observed stdout.",
                                       "float32_note": "Explicit operation rounding without FMA; not claimed to reproduce GPU compiler arithmetic exactly."},
              "comparisons": comparisons, "scope": "Post hoc pre-reset precision/integrator diagnostic only; original numerical gates and biological conclusions unchanged."}
    (output/"prefix_results.json").write_text(json.dumps(record, indent=2, allow_nan=False)+"\n")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-trace", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--frozen-diagnostic-commit", required=True)
    args = parser.parse_args()
    run(args.native_trace.resolve(), args.output.resolve(), args.frozen_diagnostic_commit)
