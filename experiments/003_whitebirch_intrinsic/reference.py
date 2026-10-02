"""Independent float64 hybrid ODE reference for the frozen CA2 step assay.

Time is in ms, voltage in mV, and current/recovery variable in pA. This
module does not import the production integrator or its reset implementation.
Simulation must be invoked only after the assay preregistration is committed.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

import numpy as np
from scipy.integrate import solve_ivp


PARAMETER_NAMES = ("C", "k", "Vr", "Vt", "a", "b", "Vpeak", "Vmin", "d")
BASELINE_END_MS = 100.0
PULSE_END_MS = 1100.0
RECORDING_END_MS = 1200.0


def canonical_parameters(parameters: Mapping) -> dict[str, float]:
    """Accept compact names or the unchanged archived CSV column names."""
    result = {}
    for name in PARAMETER_NAMES:
        key = name if name in parameters else "Izh " + name
        result[name] = float(parameters[key])
    if not all(math.isfinite(value) for value in result.values()):
        raise ValueError("Reference parameters must be finite")
    if result["C"] <= 0 or result["a"] <= 0:
        raise ValueError("Reference requires positive capacitance and recovery rate")
    if result["Vmin"] >= result["Vpeak"]:
        raise ValueError("Reset voltage must lie below the event threshold")
    return result


def holding_equilibrium(parameters: Mapping) -> dict[str, float]:
    """Solve both steady-state equations at the declared -70 mV hold."""
    p = canonical_parameters(parameters)
    voltage = -70.0
    recovery = p["b"] * (voltage - p["Vr"])
    bias = recovery - p["k"] * (voltage - p["Vr"]) * (voltage - p["Vt"])
    return {"v_mV": voltage, "u_pA": recovery, "Ihold_pA": bias}


def simulate(parameters: Mapping, current: float, rtol: float, atol: float,
             max_step: float) -> dict:
    """Integrate exact phase transitions and localized upward threshold events.

    Every sweep restarts from the same holding equilibrium (full recovery).
    A terminal upward Vpeak event ends a solve; the algebraic reset is applied
    at that time, then a fresh DOP853 solve begins. Boundary states are the
    states after any event/reset at that exact boundary. Events at 1100 ms
    are retained but excluded from the primary half-open [100, 1100) window.
    No detector exclusion or biological scoring is performed here.
    """
    p = canonical_parameters(parameters)
    if not all(math.isfinite(x) and x > 0 for x in (rtol, atol, max_step)):
        raise ValueError("Reference tolerance and max_step must be positive and finite")
    if not math.isfinite(current):
        raise ValueError("Step current must be finite")
    hold = holding_equilibrium(p)
    state = np.array([hold["v_mV"], hold["u_pA"]], dtype=np.float64)
    events = []
    boundaries = [{"time_ms": 0.0, "v_mV": float(state[0]), "u_pA": float(state[1])}]
    segments = []
    phases = (
        ("baseline", 0.0, BASELINE_END_MS, hold["Ihold_pA"]),
        ("pulse", BASELINE_END_MS, PULSE_END_MS, hold["Ihold_pA"] + current),
        ("postpulse", PULSE_END_MS, RECORDING_END_MS, hold["Ihold_pA"]),
    )
    for phase, start, end, applied_current in phases:
        time = start

        def derivative(_time, values):
            voltage, recovery = values
            return (
                (p["k"] * (voltage - p["Vr"]) * (voltage - p["Vt"])
                 - recovery + applied_current) / p["C"],
                p["a"] * (p["b"] * (voltage - p["Vr"]) - recovery),
            )

        def threshold(_time, values):
            return values[0] - p["Vpeak"]

        threshold.terminal = True
        threshold.direction = 1.0
        while time < end:
            solution = solve_ivp(
                derivative, (time, end), state, method="DOP853",
                rtol=rtol, atol=atol, max_step=max_step, events=threshold,
            )
            if not solution.success:
                raise RuntimeError(f"Reference integration failed: {solution.message}")
            segments.append({"phase": phase, "start_ms": time,
                             "end_ms": float(solution.t[-1]), "nfev": solution.nfev})
            if len(solution.t_events[0]) == 0:
                state = solution.y[:, -1].copy()
                time = end
                continue
            event_time = float(solution.t_events[0][0])
            before = solution.y_events[0][0]
            after = np.array([p["Vmin"], float(before[1]) + p["d"]], dtype=np.float64)
            if event_time <= time:
                raise RuntimeError("Reference event failed to advance time")
            events.append({"time_ms": event_time, "phase": phase,
                           "v_before": float(before[0]), "u_before": float(before[1]),
                           "v_after": float(after[0]), "u_after": float(after[1])})
            state = after
            time = event_time
        boundaries.append({"time_ms": end, "v_mV": float(state[0]), "u_pA": float(state[1])})
    return {"method": "independent scipy DOP853 hybrid ODE", "parameters": p,
            "step_current_pA": float(current), "holding": hold,
            "rtol": rtol, "atol": atol, "max_step_ms": max_step,
            "events": events, "boundary_states": boundaries, "segments": segments}
