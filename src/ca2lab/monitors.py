"""Read CARLsim binary monitors with bounds and completeness checks."""
from pathlib import Path
import struct
import numpy as np

SPIKE_DTYPE = np.dtype([("t", "<i4"), ("id", "<i4")])
VOLTAGE_DTYPE = np.dtype([("t", "<u4"), ("id", "<u4"),
                         ("v", "<f4"), ("u", "<f4"), ("I", "<f4")])


def read_spikes(path, population_size, duration_ms):
    raw = Path(path).read_bytes()
    if population_size < 1 or duration_ms < 1 or len(raw) < 20 or (len(raw) - 20) % 8:
        raise ValueError("Invalid spike monitor length or dimensions")
    magic, version, x, y, z = struct.unpack("<ifiii", raw[:20])
    if magic != 206661989 or not np.isclose(version, 0.2) or x*y*z != population_size:
        raise ValueError("Unexpected spike monitor header")
    records = np.frombuffer(raw, dtype=SPIKE_DTYPE, offset=20).copy()
    if np.any(records["t"] < 0) or np.any(records["t"] >= duration_ms):
        raise ValueError("Spike time outside trial")
    if np.any(records["id"] < 0) or np.any(records["id"] >= population_size):
        raise ValueError("Spike ID outside population")
    if len(np.unique(records)) != len(records):
        raise ValueError("Duplicate spike event")
    return records


def read_voltage(path, population_size, duration_ms):
    raw = Path(path).read_bytes()
    if population_size < 1 or duration_ms < 1 or len(raw) < 24 or (len(raw) - 24) % 20:
        raise ValueError("Invalid neuron monitor length or dimensions")
    magic, version, x, y, z, cap = struct.unpack("<ifiiii", raw[:24])
    if magic != 206661979 or not np.isclose(version, 0.1) or x*y*z != population_size or cap < 1:
        raise ValueError("Unexpected neuron monitor header")
    count = min(cap, population_size)
    records = np.frombuffer(raw, dtype=VOLTAGE_DTYPE, offset=24)
    if len(records) != count*duration_ms:
        raise ValueError("Incomplete neuron monitor")
    if np.any(records["id"] >= count) or np.any(records["t"] >= duration_ms):
        raise ValueError("Neuron monitor coordinates outside trial")
    for field in ("v", "u", "I"):
        if not np.all(np.isfinite(records[field])):
            raise ValueError(f"Nonfinite {field} record")
    indices = records["id"].astype(np.int64)*duration_ms + records["t"]
    if len(np.unique(indices)) != count*duration_ms:
        raise ValueError("Duplicate or missing neuron monitor coordinates")
    voltage = np.empty((count, duration_ms), dtype=np.float32)
    voltage[records["id"], records["t"]] = records["v"]
    return voltage
