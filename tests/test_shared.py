import io
from pathlib import Path
import struct
import tarfile
import tempfile
import unittest
import numpy as np
from ca2lab.monitors import read_spikes, read_voltage, SPIKE_DTYPE, VOLTAGE_DTYPE
from ca2lab.events import read_events, same_events
from ca2lab.decoding import spike_count_features, centroid_accuracy
from ca2lab.provenance import extract_tar, verify_file, sha256


class RecordsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
    def tearDown(self):
        self.temp.cleanup()
    def spike_file(self, rows, suffix=b""):
        path = self.root / "spikes.dat"
        path.write_bytes(struct.pack("<ifiii", 206661989, .2, 2, 1, 1) +
                         np.array(rows, dtype=SPIKE_DTYPE).tobytes() + suffix)
        return path
    def test_input_delivery_ignores_record_order(self):
        path = self.spike_file([(2, 0), (1, 1)])
        text = self.root / "events.txt"
        text.write_text("1 1\n2 0\n")
        self.assertTrue(same_events(read_spikes(path, 2, 3), read_events(text, 2, 3)))
    def test_spike_bounds_duplicates_and_truncation(self):
        for rows, suffix in [([(3, 0)], b""), ([(1, 2)], b""), ([(1, 0), (1, 0)], b""), ([], b"x")]:
            with self.subTest(rows=rows, suffix=suffix), self.assertRaises(ValueError):
                read_spikes(self.spike_file(rows, suffix), 2, 3)
    def test_event_stream_rejects_unsorted_or_invalid(self):
        path = self.root / "events.txt"
        for text in ("2 0\n1 1\n", "0 0\n0 0\n", "3 0\n", "a 0\n", "0 0 1\n"):
            path.write_text(text)
            with self.subTest(text=text), self.assertRaises(ValueError):
                read_events(path, 2, 3)
    def voltage_file(self, rows):
        path = self.root / "voltage.dat"
        path.write_bytes(struct.pack("<ifiiii", 206661979, .1, 2, 1, 1, 2) +
                         np.array(rows, dtype=VOLTAGE_DTYPE).tobytes())
        return path
    def test_voltage_complete_and_finite(self):
        rows = [(t, cell, -70+t, 0, 0) for t in range(3) for cell in range(2)]
        self.assertEqual(read_voltage(self.voltage_file(rows), 2, 3).shape, (2, 3))
        for bad in (rows[:-1], rows[:-1] + [rows[0]], rows[:-1] + [(2, 1, np.nan, 0, 0)]):
            with self.assertRaises(ValueError):
                read_voltage(self.voltage_file(bad), 2, 3)
    def test_count_bins_use_half_open_intervals(self):
        rows = np.array([(49, 0), (50, 0), (100, 1), (249, 1), (250, 0)], dtype=SPIKE_DTYPE)
        result = spike_count_features(rows, 2, [50, 100, 150, 200, 250])
        np.testing.assert_array_equal(result, [1, 0, 0, 0, 0, 1, 0, 1])
    def test_train_only_centroids_and_ties(self):
        self.assertEqual(centroid_accuracy([[0], [2]], [0, 1], [[1]], [0]), .5)
        self.assertEqual(centroid_accuracy([[0], [2]], [0, 1], [[0], [2]], [0, 1]), 1)
        # A merely close pair of distances is not an exact tie.
        self.assertEqual(centroid_accuracy([[0], [2]], [0, 1], [[1.000001]], [1]), 1)
    def test_hashes_fail_after_mutation(self):
        path = self.root / "data"
        path.write_bytes(b"original")
        expected = sha256(path)
        verify_file(path, expected)
        path.write_bytes(b"changed")
        with self.assertRaises(ValueError):
            verify_file(path, expected)
    def test_archive_rejects_traversal_and_links(self):
        for name, kind in (("../escape", tarfile.REGTYPE), ("link", tarfile.SYMTYPE)):
            archive = self.root / "unsafe.tar"
            with tarfile.open(archive, "w") as bundle:
                member = tarfile.TarInfo(name)
                member.type = kind
                member.linkname = "/tmp/escape"
                bundle.addfile(member)
            with self.assertRaises(ValueError):
                extract_tar(archive, self.root / "destination")
        self.assertFalse((self.root / "destination").exists())


if __name__ == "__main__":
    unittest.main()
