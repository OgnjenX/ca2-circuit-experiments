"""Independent high-accuracy reference for archived CARLsim RK4 clock rules.

Smooth substep spans use SciPy DOP853 rather than production RK4. Threshold
tests, reset-only iterations and millisecond refractory counters preserve the
archived CPU nine-parameter path. This is not the immediate-reset ODE assay.
Do not execute before preregistration and source-readiness gates permit runs.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

import numpy as np
from scipy.integrate import solve_ivp


NAMES = ("C", "k", "Vr", "Vt", "a", "b", "Vpeak", "Vmin", "d")
REFRACTORY_COUNTER = 1  # snn_manager.cpp:6101; archived export field is not read.


def simulate(parameters: Mapping, current: float, dt_ms: float,
             rtol: float, atol: float, max_step: float) -> dict:
    """Return crossings, clock-detected events, reset and phase-boundary states.

    Crossing times describe smooth trajectories; detection/reset happens at a
    later clock boundary with the strict previous-state V > Vpeak test. Each
    reset consumes its entire iteration. While the counter is positive both V
    and u remain frozen; the counter decreases only on the last substep of a
    millisecond. Localized crossings do not trigger immediate resets here.
    """
    p = {key: float(parameters[key] if key in parameters else parameters["Izh " + key])
         for key in NAMES}
    if not all(math.isfinite(x) for x in (*p.values(), current)):
        raise ValueError("Parameters and current must be finite")
    if p["C"] <= 0 or p["a"] <= 0 or p["Vmin"] >= p["Vpeak"]:
        raise ValueError("Invalid capacitance, recovery rate or reset voltage")
    if not all(math.isfinite(x) and x > 0 for x in (dt_ms, rtol, atol, max_step)):
        raise ValueError("Step and reference controls must be finite and positive")
    substeps = round(1.0 / dt_ms)
    if substeps < 1 or not math.isclose(substeps * dt_ms, 1.0, rel_tol=0, abs_tol=1e-12):
        raise ValueError("dt_ms must divide the archived one-millisecond clock")
    # Use integer clock indices to avoid accumulating transition-time drift.
    step = 1.0 / substeps
    state = np.array([-70.0, p["b"] * (-70.0 - p["Vr"])], dtype=np.float64)
    holding_current = float(state[1] - p["k"] * (state[0] - p["Vr"]) * (state[0] - p["Vt"]))
    initial = state.copy()
    counter = 0
    events, crossings, clamps = [], [], []
    boundaries = [{"time_ms": 0.0, "v_mV": float(state[0]), "u_pA": float(state[1]),
                   "refractory_counter": counter}]
    evaluation_count = 0
    suppressed_substeps = 0
    pending_crossing = None
    for index in range(1200 * substeps):
        start = index / substeps
        end = (index + 1) / substeps
        last_iteration = (index + 1) % substeps == 0
        phase = "baseline" if start < 100 else "pulse" if start < 1100 else "postpulse"
        applied = holding_current + (current if phase == "pulse" else 0.0)
        if counter > 0:
            suppressed_substeps += 1
            if last_iteration:
                counter -= 1
                state[0] = p["Vmin"]
        elif state[0] > p["Vpeak"]:
            before = state.copy()
            state = np.array([p["Vmin"], before[1] + p["d"]], dtype=np.float64)
            counter = REFRACTORY_COUNTER if last_iteration else REFRACTORY_COUNTER + 1
            events.append({"time_ms": start, "detection_time_ms": start,
                           "crossing_time_ms": pending_crossing,
                           "phase": phase, "clock_index": index,
                           "last_iteration": last_iteration,
                           "v_before": float(before[0]), "u_before": float(before[1]),
                           "v_after": float(state[0]), "u_after": float(state[1]),
                           "refractory_counter_after": counter,
                           "reset_iteration_end_ms": end})
            pending_crossing = None
        else:
            def rhs(_time, values):
                voltage, recovery = values
                return ((p["k"] * (voltage - p["Vr"]) * (voltage - p["Vt"])
                         - recovery + applied) / p["C"],
                        p["a"] * (p["b"] * (voltage - p["Vr"]) - recovery))

            def threshold(_time, values):
                return values[0] - p["Vpeak"]

            threshold.direction = 1.0
            threshold.terminal = False
            solved = solve_ivp(rhs, (start, end), state, method="DOP853",
                               rtol=rtol, atol=atol, max_step=max_step, events=threshold)
            if not solved.success:
                raise RuntimeError(f"Reference failed in clock span {start}..{end}: {solved.message}")
            evaluation_count += solved.nfev
            for event_time, values in zip(solved.t_events[0], solved.y_events[0]):
                event_time = float(event_time)
                # A threshold equal to a grid boundary may be rediscovered at
                # the next span start. Preserve one crossing record.
                if crossings and event_time == crossings[-1]["time_ms"]:
                    continue
                crossings.append({"time_ms": event_time, "phase": phase,
                                  "v_mV": float(values[0]), "u_pA": float(values[1]),
                                  "clock_span_start_ms": start, "clock_span_end_ms": end})
                pending_crossing = event_time
            state = solved.y[:, -1].copy()
            if state[0] < -90.0:
                clamps.append({"time_ms": end, "v_before_mV": float(state[0])})
                state[0] = -90.0  # Archived RK4 path clamps at each span end.
        if index + 1 in (100 * substeps, 1100 * substeps, 1200 * substeps):
            boundaries.append({"time_ms": end, "v_mV": float(state[0]),
                               "u_pA": float(state[1]), "refractory_counter": counter})
    return {"method": "independent DOP853 smooth spans with archived CARLsim clock semantics",
            "parameters": p, "step_current_pA": float(current), "dt_ms": step,
            "substeps_per_ms": substeps, "rtol": rtol, "atol": atol,
            "max_step_ms": max_step, "hardcoded_Izh_ref": REFRACTORY_COUNTER,
            "holding": {"v_mV": float(initial[0]), "u_pA": float(initial[1]),
                        "Ihold_pA": holding_current},
            "events": events, "crossings": crossings, "boundary_states": boundaries,
            "voltage_floor_clamps": clamps, "nfev": evaluation_count,
            "suppressed_substeps": suppressed_substeps,
            "undetected_final_crossing_time_ms": pending_crossing}
