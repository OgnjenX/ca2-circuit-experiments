"""Measurements for a bounded, subthreshold CA2 slice assay."""

from pathlib import Path
import struct

import numpy as np

from ca2lab.monitors import VOLTAGE_DTYPE


def read_voltage_window(path, population, start_ms, end_ms):
    """Require one finite record per cell and ms in an absolute-time window."""
    raw = Path(path).read_bytes()
    if len(raw) < 24 or (len(raw) - 24) % 20:
        raise ValueError("Invalid voltage length")
    magic, version, x, y, z, cap = struct.unpack("<ifiiii", raw[:24])
    if magic != 206661979 or not np.isclose(version, .1) or x*y*z != population or cap < population:
        raise ValueError("Unexpected voltage header")
    if not 0 <= start_ms < end_ms:
        raise ValueError("Invalid recording window")
    records = np.frombuffer(raw, dtype=VOLTAGE_DTYPE, offset=24)
    width = end_ms - start_ms
    if len(records) != width * population:
        raise ValueError("Incomplete recording window")
    if np.any(records['id'] >= population) or np.any(records['t'] < start_ms) or np.any(records['t'] >= end_ms):
        raise ValueError("Recording coordinates outside window")
    if any(not np.isfinite(records[field]).all() for field in ('v', 'u', 'I')):
        raise ValueError("Nonfinite state")
    offsets = records['t'].astype(np.int64) - start_ms
    indices = records['id'].astype(np.int64)*width + offsets
    if len(np.unique(indices)) != width*population:
        raise ValueError("Duplicate recording coordinates")
    voltage = np.empty((population, width), dtype=np.float32)
    voltage[records['id'], offsets] = records['v']
    return voltage


def measure_epsps(voltage, start_ms, pulses, delay_ms=1, post_ms=100):
    """Measure peaks relative to one baseline, including residual summation."""
    pulses = np.asarray(pulses, dtype=int)
    if len(pulses) == 0 or np.any(np.diff(pulses) <= 0):
        raise ValueError("Invalid pulse sequence")
    first = int(pulses[0]) - start_ms
    if first < 100:
        raise ValueError("Insufficient prestimulus baseline")
    baseline_segment = voltage[:, first-100:first]
    baseline = baseline_segment.mean(axis=1)
    drift = np.abs(baseline_segment[:, -20:].mean(axis=1) - baseline_segment[:, :20].mean(axis=1))
    peaks = []
    for index, pulse in enumerate(pulses):
        begin = int(pulse) + delay_ms - start_ms
        end = (int(pulses[index+1]) + delay_ms if index+1 < len(pulses)
               else int(pulse)+post_ms) - start_ms
        if begin < 0 or end > voltage.shape[1] or end <= begin:
            raise ValueError("Peak window outside recording")
        peaks.append(voltage[:, begin:end].max(axis=1) - baseline)
    peaks = np.asarray(peaks)
    if np.any(peaks[0] <= 0):
        raise ValueError("Nonpositive initial EPSP")
    ratios = peaks / peaks[0]
    return {
        'baseline_mV': float(baseline.mean()),
        'max_baseline_drift_mV': float(drift.max()),
        'mean_peaks_mV': peaks.mean(axis=1).tolist(),
        'mean_ratios': ratios.mean(axis=1).tolist(),
        'cell_ratios': ratios[-1].tolist(),
        'ratio_sd_model_cells': float(ratios[-1].std(ddof=1)),
    }
