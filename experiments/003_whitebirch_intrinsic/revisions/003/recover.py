"""Serializer-only recovery of completed revision-002 numerical work.

Never launches native neurons or reintegrates clock references. Original
references and failed outputs remain untouched. The immediate diagnostic uses
the unchanged frozen revision-002 implementation after the recovery freeze.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

SOURCE_FREEZE = "233b068cb7e22663b9ce551806e4a4e573a63872"
HERE = Path(__file__).resolve().parent
ASSAY = HERE.parents[1]
ROOT = ASSAY.parents[1]
V2 = ASSAY/"revisions"/"002"
sys.path.insert(0, str(V2))
spec = importlib.util.spec_from_file_location("frozen_numerics_v2", V2/"numerics.py")
numerics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(numerics)


def normalize(value):
    """Convert NumPy scalars only at the JSON write boundary."""
    if isinstance(value, np.generic):
        return normalize(value.item())
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize(item) for item in value]
    return value


def write_json(path, record):
    Path(path).write_text(json.dumps(normalize(record), indent=2, allow_nan=False)+"\n")


def freeze_gate(recovery_commit):
    frozen = numerics.verify_frozen_inputs(SOURCE_FREEZE)
    if frozen != SOURCE_FREEZE:
        raise ValueError("Wrong scientific source freeze")
    commit = subprocess.check_output(["git", "rev-parse", recovery_commit], cwd=ROOT, text=True).strip()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    subprocess.run(["git", "merge-base", "--is-ancestor", SOURCE_FREEZE, commit], cwd=ROOT, check=True)
    subprocess.run(["git", "merge-base", "--is-ancestor", commit, head], cwd=ROOT, check=True)
    manifest_path = HERE/"preregistration_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if manifest["source_freeze_commit"] != SOURCE_FREEZE:
        raise ValueError("Recovery manifest scientific freeze mismatch")
    pinned = manifest["sha256"]
    if "revisions/003/recover.py" not in pinned:
        raise ValueError("Recovery code not pinned by recovery manifest")
    for relative in set(pinned) | {"revisions/003/preregistration_manifest.json"}:
        path = ASSAY/relative
        committed = subprocess.check_output(["git", "show", f"{commit}:{path.relative_to(ROOT)}"], cwd=ROOT)
        if committed != path.read_bytes() or (relative in pinned and numerics.sha256(path) != pinned[relative]):
            raise ValueError(f"Recovery freeze differs: {relative}")
    # Verify every scientific source pin, not only the controller's direct imports.
    source_manifest = json.loads((V2/"preregistration_manifest.json").read_text())
    for relative, digest in source_manifest["sha256"].items():
        if numerics.sha256(ASSAY/relative) != digest:
            raise ValueError(f"Scientific source pin changed: {relative}")
    return commit, manifest, source_manifest


def reference_identity(reference, metadata, controls):
    expected_parameters = metadata["parameters_float32"]
    expected = {"parameters": expected_parameters, "step_current_pA": float(metadata["step_current_pA"]),
                "dt_ms": 1/metadata["steps_per_ms"], "substeps_per_ms": metadata["steps_per_ms"],
                "rtol": controls[0], "atol": controls[1], "max_step_ms": controls[2],
                "hardcoded_Izh_ref": 1,
                "holding": {"v_mV": -70., "u_pA": metadata["initial_u_float32_pA"],
                            "Ihold_pA": metadata["holding_float32_pA"]}}
    if any(reference.get(key) != value for key, value in expected.items()):
        raise ValueError("Existing reference configuration differs from native/frozen controls")
    boundaries = reference.get("boundary_states", [])
    if [row.get("time_ms") for row in boundaries] != [0., 100., 1100., 1200.]:
        raise ValueError("Existing reference has incomplete phase boundaries")


def recover(workspace, references_dir, output, recovery_commit):
    recovery_commit, manifest, source_manifest = freeze_gate(recovery_commit)
    if output.exists():
        raise ValueError("Recovery requires a fresh output directory")
    # Pin all pre-existing inputs before any diagnostic integration or output.
    reference_pins = manifest["reference_sha256"]
    expected_names = {f"rk{steps}_step{current}_reference_{label}.json"
                      for steps in numerics.DT_STEPS for current in numerics.CURRENTS for label in ("loose", "tight")}
    if set(reference_pins) != expected_names:
        raise ValueError("Recovery manifest must pin all 66 existing references")
    for name, digest in reference_pins.items():
        if numerics.sha256(references_dir/name) != digest:
            raise ValueError(f"Existing reference checksum differs: {name}")
    native_pins = manifest.get("native_sha256", {})
    native_names = {f"rk{steps}_step{current}{suffix}" for steps in numerics.DT_STEPS
                    for current in numerics.CURRENTS for suffix in (".csv", ".stdout", ".stderr", ".exit.json")}
    if set(native_pins) != native_names:
        raise ValueError("Recovery manifest must pin all 132 native trace and sidecar files")
    for name, digest in native_pins.items():
        candidates = list(workspace.rglob(name))
        if len(candidates) != 1 or numerics.sha256(candidates[0]) != digest:
            raise ValueError(f"Native input checksum differs: {name}")
    records, hashes = [], {}
    traces = sorted(workspace.rglob("rk*_step*.csv"))
    if len(traces) != 33:
        raise ValueError("Recovery requires the complete native 33-sweep grid")
    for trace in traces:
        metadata, stdout = numerics.metadata_for(workspace, trace, SOURCE_FREEZE, source_manifest["runtime_pins"])
        record = numerics.validate_trace(trace, metadata)
        for path in (trace, stdout, trace.with_suffix(".stderr"), trace.with_suffix(".exit.json")):
            hashes[str(path)] = numerics.sha256(path)
        references = []
        for label, controls in zip(("loose", "tight"), numerics.REFERENCE_CONTROLS):
            path = references_dir/f"{trace.stem}_reference_{label}.json"
            reference = json.loads(path.read_text())
            reference_identity(reference, metadata, controls)
            references.append(reference)
            hashes[str(path)] = numerics.sha256(path)
        loose, tight = references
        checks = [numerics.validate_clock_reference(r) for r in references]
        record.update(reference_reset_audit={"pass": all(c["pass"] for c in checks), "loose": checks[0], "tight": checks[1]},
                      reference_refinement_crossings=numerics.compare_events(loose, tight),
                      reference_refinement_detections=numerics.compare_events(loose, tight, "events"),
                      same_grid_crossings=numerics.compare_events(record, tight),
                      same_grid_detections=numerics.compare_events(record, tight, "events"),
                      reference_raw_files=[str(references_dir/f"{trace.stem}_reference_{x}.json") for x in ("loose", "tight")])
        records.append(record)
        print(f"Recovered unchanged checks for {trace.stem}; no reintegration", flush=True)
    result = numerics.validate_records(records)
    result.update(records=records, raw_file_sha256=hashes, frozen_commit=SOURCE_FREEZE,
                  recovery_commit=recovery_commit, serializer_recovery_only=True,
                  controls={"reference": numerics.REFERENCE_CONTROLS, "production_steps_per_ms": numerics.DT_STEPS},
                  initial_state_note="Actual native float32 configuration preserved; unchanged frozen numerical checks.")
    output.mkdir(parents=True, exist_ok=False)
    write_json(output/"numerical_checks.json", result)
    # This unchanged frozen function generates ordinary Python-scalar diagnostic
    # results; it is independent of native NumPy-array comparisons that failed.
    diagnostic = numerics.immediate_diagnostic(records, output, SOURCE_FREEZE)
    write_json(output/"immediate_diagnostic.json", diagnostic)
    result.update(immediate_diagnostic_passed=diagnostic["passed"],
                  immediate_diagnostic_sha256=numerics.sha256(output/"immediate_diagnostic.json"))
    write_json(output/"numerical_checks.json", result)
    return normalize(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--references", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--recovery-commit", required=True)
    args = parser.parse_args()
    result = recover(args.workspace.resolve(), args.references.resolve(), args.output.resolve(), args.recovery_commit)
    print(json.dumps({"passed": result["passed"], "diagnostic_passed": result["immediate_diagnostic_passed"]}))
    raise SystemExit(0 if result["passed"] else 1)
