"""Generic synthetic tests only: no CA2 parameters, ODE runs or target data."""
import csv
import json
import tempfile
import unittest
from pathlib import Path

import numerics


def metadata(current=0):
    return {"mode": "GPU_MODE", "steps_per_ms": 20, "step_current_pA": current,
            "parameters_float32": {"C": 100., "k": 1., "Vr": -70., "Vt": -50.,
                                   "a": .125, "b": 0., "Vpeak": 30., "Vmin": -70., "d": 2.},
            "holding_float32_pA": 0., "pulse_float32_pA": float(current),
            "initial_u_float32_pA": 0., "dt_ms": .05, "Izh_ref": 1}


def flat_rows():
    return [[i/20, -70., 0., 0, 0] for i in range(24001)]


def reset_rows():
    rows = flat_rows()
    rows[10][1] = 31.  # Smooth span crosses threshold ending at 0.5 ms.
    for i in range(11, len(rows)):
        rows[i][2] = 2.
        rows[i][3] = 2 if i < 20 else 1 if i < 40 else 0
        rows[i][4] = int(i <= 20)  # Millisecond latch; does not define AP count.
    return rows


class SyntheticNumericalTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name)/"synthetic.csv"

    def validate(self, rows, config=None):
        with self.path.open("w") as stream:
            writer = csv.writer(stream)
            writer.writerow(["time_ms", "v_mV", "u_pA", "ref_counter", "curSpike"])
            writer.writerows(rows)
        return numerics.validate_trace(self.path, config or metadata())

    def test_flat_hold(self):
        record = self.validate(flat_rows())
        self.assertTrue(record["trace_rules_pass"])
        self.assertEqual(record["events"], [])
        self.assertEqual(record["crossings"], [])

    def test_reset_and_counter_freeze(self):
        record = self.validate(reset_rows(), metadata(100))
        self.assertEqual(record["reset_rule_errors"], [])
        self.assertEqual(len(record["events"]), 1)
        self.assertEqual(len(record["crossings"]), 1)
        event = record["events"][0]
        self.assertEqual(event["time_ms"], .5)
        self.assertEqual(event["u_after"], 2.)
        self.assertEqual(event["refractory_counter_after"], 2)

    def test_damaged_reset_and_signal(self):
        for column, value in ((2, 2.25), (4, 0)):
            with self.subTest(column=column):
                rows = reset_rows()
                rows[11][column] = value
                record = self.validate(rows, metadata(100))
                self.assertTrue(any(e["kind"] == "reset_state" for e in record["reset_rule_errors"]))

    def test_damaged_refractory_freeze_and_decrement(self):
        for row, column, value in ((12, 2, 2.25), (12, 1, -69.), (19, 3, 1), (20, 3, 2)):
            with self.subTest(row=row, column=column):
                rows = reset_rows()
                rows[row][column] = value
                record = self.validate(rows, metadata(100))
                self.assertTrue(any(e["kind"] == "refractory_freeze" for e in record["reset_rule_errors"]))

    def test_trace_completeness_clock_and_float32(self):
        for case in ("missing", "clock", "nonfinite", "nonfloat32"):
            with self.subTest(case=case):
                rows = flat_rows()
                if case == "missing": rows.pop()
                if case == "clock": rows[10][0] += .001
                if case == "nonfinite": rows[10][1] = float("nan")
                if case == "nonfloat32": rows[10][2] = .1
                with self.assertRaises(ValueError): self.validate(rows)

    def test_exact_metadata(self):
        numerics.validate_metadata(metadata())
        for key, value in (("mode", "CPU_MODE"), ("steps_per_ms", 20.),
                           ("step_current_pA", 101), ("holding_float32_pA", .1),
                           ("pulse_float32_pA", 1.), ("dt_ms", .025), ("Izh_ref", 2)):
            with self.subTest(key=key):
                config = metadata()
                config[key] = value
                with self.assertRaises(ValueError): numerics.validate_metadata(config)
        config = metadata()
        config["parameters_float32"]["extra"] = 1.
        with self.assertRaises(ValueError): numerics.validate_metadata(config)

    def test_halfopen_endpoint_and_detector(self):
        times = [0., 100., 105., 106., 1100., 1200.]
        self.assertEqual(numerics.phase_counts(times), {"pre": 1, "pulse": 3, "post": 2})
        audit = numerics.detector_audit(times)
        self.assertEqual(audit["pulse_inclusive_count"], 4)
        self.assertEqual(audit["compatible_counts"]["pulse"], 2)
        self.assertEqual(audit["nearest_phase_boundaries"]["1100"]["distance_ms"], 0)

    def test_native_exit_and_pin_identity(self):
        trace = Path(self.folder.name)/"rk20_step0.csv"
        trace.write_text("synthetic placeholder")
        config = metadata()
        pins = {"library_sha256": "synthetic-library", "header_sha256": "synthetic-header",
                "harness_sha256": "synthetic-harness"}
        config.update(pins)
        trace.with_suffix(".stdout").write_text(json.dumps(config)+"\n")
        trace.with_suffix(".stderr").write_text("")
        original = {"exit_code": 0, "metadata_matches_freeze": True, "frozen_commit": "synthetic-freeze",
                    "metadata": config, "failure": None}

        def checker(stdout, steps, current, runtime_pins):
            actual = json.loads(stdout)
            if actual != {**metadata(current), **runtime_pins}:
                raise ValueError("Synthetic native identity differs from pins")
            return actual

        exit_path = trace.with_suffix(".exit.json")
        exit_path.write_text(json.dumps(original))
        actual, _ = numerics.metadata_for(Path(self.folder.name), trace, "synthetic-freeze", pins, checker)
        self.assertEqual(actual, config)
        for key, value in (("exit_code", 1), ("metadata_matches_freeze", False),
                           ("frozen_commit", "wrong"), ("metadata", metadata())):
            with self.subTest(key=key):
                damaged = dict(original)
                damaged[key] = value
                exit_path.write_text(json.dumps(damaged))
                with self.assertRaises(ValueError):
                    numerics.metadata_for(Path(self.folder.name), trace, "synthetic-freeze", pins, checker)
        exit_path.write_text(json.dumps(original))
        with self.assertRaises(ValueError):
            numerics.metadata_for(Path(self.folder.name), trace, "synthetic-freeze",
                                  {**pins, "library_sha256": "wrong"}, checker)
        trace.with_suffix(".stderr").unlink()
        with self.assertRaises(ValueError):
            numerics.metadata_for(Path(self.folder.name), trace, "synthetic-freeze", pins, checker)

    def test_reference_reset_audit(self):
        p = metadata()["parameters_float32"]
        reference = {"parameters": p, "substeps_per_ms": 20, "step_current_pA": 100,
                     "events": [{"clock_index": 10, "v_before": 31., "u_before": 0.,
                                 "v_after": -70., "u_after": 2., "last_iteration": False,
                                 "refractory_counter_after": 2}], "crossings": [],
                     "boundary_states": [{"time_ms": 0, "v_mV": -70}, {"time_ms": 100, "v_mV": -70}]}
        self.assertTrue(numerics.validate_clock_reference(reference)["pass"])
        reference["events"][0]["u_after"] += 1e-6
        self.assertFalse(numerics.validate_clock_reference(reference)["pass"])


if __name__ == "__main__":
    unittest.main()
