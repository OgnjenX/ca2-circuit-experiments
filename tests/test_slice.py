"""Check scientific measurement conventions and partial monitor validation."""

from pathlib import Path
import struct
import tempfile
import unittest

import numpy as np

from ca2lab.monitors import VOLTAGE_DTYPE
from ca2lab.slice import measure_epsps, read_voltage_window


class SliceMeasurementTest(unittest.TestCase):
    def test_residual_depolarization_is_part_of_peak(self):
        voltage = np.full((2, 250), -70., dtype=np.float32)
        voltage[:, 111] = -68.
        voltage[:, 120:130] = -68.5
        voltage[:, 131] = -66.
        result = measure_epsps(voltage, 0, [110, 130])
        self.assertEqual(result['mean_ratios'], [1., 2.])
        self.assertEqual(result['mean_peaks_mV'], [2., 4.])

    def test_duplicate_missing_and_outside_window_records_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'window.dat'
            rows = [(t, cell, -70, 0, 0) for t in range(4950, 4953) for cell in range(2)]
            def save(records):
                path.write_bytes(struct.pack('<ifiiii', 206661979, .1, 2, 1, 1, 128)
                                 + np.array(records, dtype=VOLTAGE_DTYPE).tobytes())
            save(rows)
            self.assertEqual(read_voltage_window(path, 2, 4950, 4953).shape, (2, 3))
            full = [(t, cell, -70, 0, 0) for t in range(4953) for cell in range(2)]
            save(full)
            self.assertEqual(read_voltage_window(path, 2, 4950, 4953).shape, (2, 3))
            for bad in (rows[:-1], rows[:-1]+[rows[0]], rows[:-1]+[(4953, 1, -70, 0, 0)]):
                save(bad)
                with self.assertRaises(ValueError):
                    read_voltage_window(path, 2, 4950, 4953)

    def test_zero_initial_response_is_not_a_zero_ratio(self):
        with self.assertRaises(ValueError):
            measure_epsps(np.full((2, 250), -70.), 0, [110, 130])


if __name__ == '__main__':
    unittest.main()
