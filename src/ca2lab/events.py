"""Validate explicit, sorted (time_ms, cell_id) stimulus streams."""
from pathlib import Path
import numpy as np
from .monitors import SPIKE_DTYPE


def read_events(path, population_size, duration_ms):
    rows = []
    for line in Path(path).read_text().splitlines():
        values = line.split()
        if len(values) != 2:
            raise ValueError("Each event needs time and cell ID")
        time, cell = map(int, values)
        if not (0 <= time < duration_ms and 0 <= cell < population_size):
            raise ValueError("Event outside trial or population")
        rows.append((time, cell))
    if rows != sorted(set(rows)):
        raise ValueError("Events must be sorted and unique")
    return np.array(rows, dtype=SPIKE_DTYPE)


def same_events(left, right):
    """Allow monitor record order to differ from the input text order."""
    return np.array_equal(np.sort(left, order=["t", "id"]),
                          np.sort(right, order=["t", "id"]))
