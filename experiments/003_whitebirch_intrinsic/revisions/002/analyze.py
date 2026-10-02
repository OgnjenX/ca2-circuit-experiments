"""Pre-run, gate-controlled descriptive scoring for revision 002.

Importing this file performs no simulation or biological comparison. One-second
counts are rates in spikes/second. Missing means are never imputed. This module
requires a fresh output directory and never edits the preserved revision 1.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


def _finite(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Nonfinite scoring input")
    return number


def scoring_bounds(model_counts, target_rows):
    """Conservative Cartesian-product bounds; no covariance/CI assumptions.

    Counts can be a current->count mapping or an ordered sequence matching rows.
    Bounds describe figure reading uncertainty, including any explicitly
    conditional occlusion interval. They are not statistical confidence limits.
    No representative point is assigned to a missing target mean.
    """
    rows = list(target_rows)
    if not rows:
        raise ValueError("Empty target")
    if isinstance(model_counts, dict):
        counts = [model_counts[r["current_pA"]] if r["current_pA"] in model_counts
                  else model_counts[str(r["current_pA"])] for r in rows]
    else:
        counts = list(model_counts)
    if len(counts) != len(rows):
        raise ValueError("Counts and target lengths differ")
    if len({r["current_pA"] for r in rows}) != len(rows):
        raise ValueError("Duplicate target currents")
    output, squared_low, squared_high, abs_low, abs_high, point_errors = [], [], [], [], [], []
    for count, target in zip(counts, rows):
        model = _finite(count)
        if model < 0:
            raise ValueError("Negative count")
        low, high = map(_finite, target["mean_interval_Hz"])
        if low < 0 or high < low:
            raise ValueError("Invalid target interval")
        residual_low, residual_high = model-high, model-low
        minimum_abs = 0.0 if residual_low <= 0 <= residual_high else min(abs(residual_low), abs(residual_high))
        maximum_abs = max(abs(residual_low), abs(residual_high))
        mean = target.get("mean_Hz")
        point = None if mean is None else model-_finite(mean)
        if mean is not None and not low <= mean <= high:
            raise ValueError("Visible mean outside reading interval")
        if point is not None:
            point_errors.append(point)
        squared_low.append(minimum_abs**2)
        squared_high.append(maximum_abs**2)
        abs_low.append(minimum_abs)
        abs_high.append(maximum_abs)
        output.append({"current_pA": target["current_pA"], "model_count_1s": model,
                       "model_rate_Hz": model, "paper_mean_Hz": mean,
                       "paper_mean_interval_Hz": [low, high],
                       "paper_SEM_Hz": target.get("SEM_Hz"),
                       "residual_interval_Hz": [residual_low, residual_high],
                       "visible_mean_residual_Hz": point,
                       "target_status": target.get("status")})
    size = len(rows)
    primary = {
        "n": size,
        "signed_mean_error_bounds_Hz": [sum(r["residual_interval_Hz"][0] for r in output)/size,
                                        sum(r["residual_interval_Hz"][1] for r in output)/size],
        "RMSE_bounds_Hz": [math.sqrt(sum(squared_low)/size), math.sqrt(sum(squared_high)/size)],
        "max_absolute_error_bounds_Hz": [max(abs_low), max(abs_high)],
        "point_metrics": None,
        "interpretation": "Conditional figure-reading bounds, not confidence intervals or biological equivalence limits.",
    }
    secondary = None
    if point_errors:
        secondary = {"n": len(point_errors),
                     "signed_mean_error_Hz": sum(point_errors)/len(point_errors),
                     "RMSE_Hz": math.sqrt(sum(x*x for x in point_errors)/len(point_errors)),
                     "max_absolute_error_Hz": max(map(abs, point_errors)),
                     "interpretation": "Secondary visible-mean point summary; excludes missing means and is not the primary all-current result."}
    return {"rows": output, "primary_all_current_bounds": primary,
            "secondary_visible_mean_point_summary": secondary}


def primary_records(numerics):
    if numerics.get("passed") is not True:
        raise ValueError("Primary numerical verification has not passed")
    records = numerics.get("records", [])
    grid = [(r.get("metadata", {}).get("steps_per_ms"),
             r.get("metadata", {}).get("step_current_pA")) for r in records]
    if len(grid) != 33 or set(grid) != {(step, current) for step in (20, 40, 80)
                                      for current in range(0, 1001, 100)}:
        raise ValueError("Native numerical grid incomplete or duplicated")
    required = ("trace_rules_pass", "same_grid_crossings", "same_grid_detections",
                "reference_refinement_crossings", "reference_refinement_detections", "reference_reset_audit")
    for record in records:
        for key in required:
            value = record.get(key)
            if (value.get("pass") if isinstance(value, dict) else value) is not True:
                raise ValueError(f"Numerical record gate failed: {key}")
    refinements = numerics.get("production_timestep_refinements", [])
    if len(records) != 33 or len(refinements) != 33 or any(x.get("pass") is not True for x in refinements):
        raise ValueError("Incomplete native/reference numerical verification")
    selected = [r for r in records if r["metadata"]["steps_per_ms"] == 80]
    currents = [r["metadata"]["step_current_pA"] for r in selected]
    if len(selected) != 11 or set(currents) != set(range(0, 1001, 100)):
        raise ValueError("Actual finest native records incomplete or duplicated")
    return {r["metadata"]["step_current_pA"]: r for r in selected}


def diagnostic_counts(diagnostic):
    """Accept separately verified diagnostic records, never a replacement curve.

    Runner contract: passed=true plus eleven records, each with step_current_pA,
    events[{time_ms}], refinement_pass=true, and loose_metrics/tight_metrics
    each with reset_states_pass=true and holding_check_pass=true. The runner
    must compare two independently refined immediate-reset references before
    emitting these gates. This scorer does not integrate an ODE.
    """
    if diagnostic is None or diagnostic.get("passed") is not True:
        return None
    records = diagnostic.get("records", [])
    currents = [r.get("step_current_pA") for r in records]
    if len(records) != 11 or set(currents) != set(range(0, 1001, 100)):
        raise ValueError("Immediate-reset diagnostic verification incomplete")
    counts = {}
    for record in records:
        if record.get("refinement_pass") is not True or any(
            record.get(key, {}).get("reset_states_pass") is not True
            or record.get(key, {}).get("holding_check_pass") is not True
            for key in ("loose_metrics", "tight_metrics")
        ):
            raise ValueError("Immediate-reset diagnostic record has not passed")
        times = [_finite(event["time_ms"]) for event in record["events"]]
        if any(b <= a for a, b in zip(times, times[1:])):
            raise ValueError("Immediate-reset events unordered")
        counts[record["step_current_pA"]] = sum(100 <= t < 1100 for t in times)
    return counts


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _fmt(number):
    return "missing" if number is None else f"{number:.4f}"


def _interval(values):
    return f"[{_fmt(values[0])}, {_fmt(values[1])}]"


def plot_comparison(comparison, diagnostic, path):
    import matplotlib
    if matplotlib.__version__ != "3.10.7":
        raise RuntimeError(f"Expected pinned Matplotlib 3.10.7, found {matplotlib.__version__}")
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = comparison["rows"]
    figure, axis = plt.subplots(figsize=(8.6, 5.7), constrained_layout=True)
    visible = [r for r in rows if r["paper_mean_Hz"] is not None]
    xs = [r["current_pA"] for r in visible]
    means = [r["paper_mean_Hz"] for r in visible]
    errors = [[r["paper_mean_Hz"]-r["paper_mean_interval_Hz"][0] for r in visible],
              [r["paper_mean_interval_Hz"][1]-r["paper_mean_Hz"] for r in visible]]
    axis.errorbar(xs, means, yerr=errors, fmt="o", color="#175fc7", capsize=4,
                  label="Paper: nine readable control means + reading bounds", zorder=4)
    hidden = [r for r in rows if r["paper_mean_Hz"] is None]
    for index, row in enumerate(hidden):
        low, high = row["paper_mean_interval_Hz"]
        axis.vlines(row["current_pA"], low, high, color="#175fc7", linewidth=3,
                    label="100 pA: conditional occlusion interval; no mean" if index == 0 else None)
        axis.hlines([low, high], row["current_pA"]-8, row["current_pA"]+8, color="#175fc7", linewidth=2)
    axis.plot([r["current_pA"] for r in rows], [r["model_rate_Hz"] for r in rows],
              "s-", color="#bf5527", label="Primary: actual GPU, 80 substeps/ms", markersize=5)
    if diagnostic is not None:
        axis.plot(sorted(k for k in diagnostic if k > 0), [diagnostic[k] for k in sorted(diagnostic) if k > 0],
                  "^--", color="#7451a8", label="Separate immediate-reset semantics diagnostic", markersize=5)
    axis.set(xlabel="Added 1 s current step above holding bias (pA)", ylabel="Pulse firing count / 1 s (spikes/s)",
             title="Frozen CA2 point neuron versus Whitebirch 2022 Figure 1C controls")
    axis.set_xticks(range(100, 1001, 100))
    axis.set_ylim(bottom=-.5)
    axis.grid(alpha=.18)
    axis.legend(loc="best", fontsize=8)
    figure.text(.02, -.018, "Paper SEM endpoints are missing, not zero. Reading intervals are not confidence intervals.\n"
                "100 pA interval assumes a plotted control marker hidden by red overdraw. No simulated variance.", fontsize=8)
    figure.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(figure)


def report_text(comparison, numerics, records, diagnostic, target):
    primary = comparison["primary_all_current_bounds"]
    secondary = comparison["secondary_visible_mean_point_summary"]
    lines = ["# Whitebirch intrinsic benchmark — revision 002", "",
             "The actual unchanged GPU backend passed the preregistered independent numerical gates. "
             "The following discrepancies are descriptive comparisons with a published population mean curve; "
             "no biological equivalence margin or population validation pass/fail is supplied.", "",
             "All-ten bounds are conditional on the 100 pA control marker having been plotted and hidden by red overdraw. "
             "Its mean has no identifiable point estimate. Without that plotting assumption, all-ten scores are unavailable.", "",
             "| Added current (pA) | Actual 1 s count | Paper mean (Hz) | Paper reading interval (Hz) | Residual interval (Hz) | Visible-mean residual (Hz) |",
             "|---:|---:|---:|---:|---:|---:|"]
    for row in comparison["rows"]:
        lines.append(f"| {row['current_pA']} | {row['model_count_1s']:g} | {_fmt(row['paper_mean_Hz'])} | "
                     f"{_interval(row['paper_mean_interval_Hz'])} | {_interval(row['residual_interval_Hz'])} | {_fmt(row['visible_mean_residual_Hz'])} |")
    lines += ["", "Residual sign is model minus paper. For the ten currents, conditional signed mean error bounds are "
              f"{_interval(primary['signed_mean_error_bounds_Hz'])} spikes/s; RMSE bounds "
              f"{_interval(primary['RMSE_bounds_Hz'])} spikes/s; maximum absolute error bounds "
              f"{_interval(primary['max_absolute_error_bounds_Hz'])} spikes/s. These conservative figure-reading bounds "
              "are not confidence intervals. No ten-point metric estimate is computed.", ""]
    if secondary:
        lines += [f"The secondary summary for the {secondary['n']} visible means has signed mean error "
                  f"{_fmt(secondary['signed_mean_error_Hz'])}, RMSE {_fmt(secondary['RMSE_Hz'])}, and maximum absolute error "
                  f"{_fmt(secondary['max_absolute_error_Hz'])} spikes/s. It excludes the hidden 100 pA mean and is not a primary substitute.", ""]
    lines += ["![Conditional descriptive comparison](comparison.png)", "",
              "The source reports 92 NON-PILO control cells from 48 mice. Controls received methylatropine, diazepam, "
              "and levetiracetam. The target is the 1 s, 100–1000 pA step assay at a −70 mV holding potential, "
              "32 °C, in 14–18-week mice of both sexes on an F1 background, using dorsal/intermediate acute slices. "
              "PILO non-SE cells and the unresolved ramp assay are excluded. All paper SEM endpoints are missing "
              "in this extraction and are not plotted or treated as zero.", "",
              "Each sweep uses its recorded holding bias plus the added step and restarts from the same prescribed "
              "float32 holding state. This assumes full recovery because experimental inter-sweep timing is unknown. "
              "Counts use localized threshold crossings in the half-open pulse interval [100,1100) ms, with 100 ms "
              "baseline and postpulse windows. Reset markers do not support AP width or waveform claims.", "",
              "| Added current (pA) | Pre count | Pulse raw | Post count | Pulse detector-compatible | Pulse delayed detection | Minimum whole-trace ISI (ms) |",
              "|---:|---:|---:|---:|---:|---:|---:|"]
    for current, record in sorted(records.items()):
        ca, da = record["crossing_audit"], record["detection_audit"]
        raw = ca["raw_counts"]
        lines.append(f"| {current} | {raw['pre']} | {raw['pulse']} | {raw['post']} | "
                     f"{ca['compatible_counts']['pulse']} | {da['raw_counts']['pulse']} | {_fmt(ca['minimum_ISI_ms'])} |")
    unresolved = numerics.get("comparability_unresolved", False)
    lines += ["", "Measurement comparability is unresolved." if unresolved else
              "The recorded phase, detection and detector-compatible counts agree under the declared adapter; the adapter remains an event-based approximation of the paper's trace detector.",
              "The paper's code detects peaks ≥60 mV above baseline separated by ≥6 ms, apparently over the imported trace. "
              "The instantaneous/reset model is scored by localized events, with ISI exclusion and pre/post/delayed "
              "counts audited separately. The full numerical record retains crossing brackets and endpoint ambiguity checks.", ""]
    if diagnostic is not None:
        lines += ["The immediate-reset curve is a separately refined semantics diagnostic. It is neither the actual GPU "
                  "result nor a replacement selected to improve agreement.", ""]
    else:
        lines += ["A verified immediate-reset semantics diagnostic was not supplied; no diagnostic curve is plotted.", ""]
    lines += ["This comparison concerns somatic firing counts of this frozen point neuron only. It does not validate "
              "synapses, networks, individual-cell tolerance or Hippocampome generally. No temperature compensation, "
              "current fitting, optimization, artificial cell sample, simulated SEM or independent-point chi-square is used. "
              "Repeated currents, cells nested within mice and unavailable covariance limit population inference.", "",
              "Frozen inputs and evidence hashes are listed in comparison.json; numerical_checks.json supplies the "
              "independent integration, reset, refractory, holding and timestep evidence. The prior revision report is preserved.", ""]
    return "\n".join(lines)


def run(numerics_path, target_path, output, diagnostic_path=None):
    output.mkdir(parents=True, exist_ok=False)
    numerics = json.loads(numerics_path.read_text())
    try:
        records = primary_records(numerics)
    except (ValueError, KeyError, TypeError) as error:
        (output/"report.md").write_text("# Whitebirch intrinsic benchmark — revision 002\n\n"
                                       "Primary numerical verification failed or is incomplete. Biological discrepancy scoring "
                                       "and the agreement plot were not generated.\n\n"
                                       f"Gate reason: {error}\n\nNumerical failure: {numerics.get('failure', 'see numerical_checks.json')}\n")
        return {"scored": False, "reason": str(error)}
    # Target access and comparison occur only after all primary numerical gates.
    target = json.loads(target_path.read_text())
    rows = target["rows"]
    if len(rows) != 10 or {r["current_pA"] for r in rows} != set(range(100, 1001, 100)):
        raise ValueError("All ten declared target intervals are required")
    if rows[0]["current_pA"] != 100 or rows[0]["mean_Hz"] is not None:
        raise ValueError("100 pA point estimate must remain missing")
    if any(row.get("mean_Hz") is None for row in rows[1:]):
        raise ValueError("Nine visible target means are required")
    counts = {current: record["crossing_audit"]["raw_counts"]["pulse"] for current, record in records.items()}
    comparison = scoring_bounds(counts, rows)
    diagnostic_document = json.loads(diagnostic_path.read_text()) if diagnostic_path else None
    diagnostic = diagnostic_counts(diagnostic_document)
    comparison.update(conditional_assumption=target["conditional_assumption"],
                      numerically_valid_for_scoring=True,
                      measurement_comparability_unresolved=numerics.get("comparability_unresolved", False),
                      primary_steps_per_ms=80,
                      diagnostic_status="verified separate semantics diagnostic" if diagnostic is not None else "unverified or absent; omitted",
                      input_sha256={"numerics": _sha(numerics_path), "target": _sha(target_path),
                                    "diagnostic": _sha(diagnostic_path) if diagnostic_path else None})
    # No result files are written until plotting dependencies and diagnostics pass.
    plot_comparison(comparison, diagnostic, output/"comparison.png")
    (output/"comparison.json").write_text(json.dumps(comparison, indent=2)+"\n")
    with (output/"comparison.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["current_pA", "model_count_1s", "paper_mean_Hz", "paper_interval_low_Hz",
                         "paper_interval_high_Hz", "residual_low_Hz", "residual_high_Hz", "visible_mean_residual_Hz", "paper_SEM_Hz"])
        for row in comparison["rows"]:
            writer.writerow([row["current_pA"], row["model_count_1s"], row["paper_mean_Hz"],
                             *row["paper_mean_interval_Hz"], *row["residual_interval_Hz"],
                             row["visible_mean_residual_Hz"], row["paper_SEM_Hz"]])
    (output/"report.md").write_text(report_text(comparison, numerics, records, diagnostic, target))
    return {"scored": True, "output": str(output)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--numerics", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--diagnostic", type=Path)
    args = parser.parse_args()
    result = run(args.numerics, args.target, args.output, args.diagnostic)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["scored"] else 1)


if __name__ == "__main__":
    main()
