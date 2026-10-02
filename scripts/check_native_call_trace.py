"""Compare harness API calls with the frozen experiment, without simulating neurons."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "models/ca2_carlsim"
FROZEN = ROOT / "experiments/001_input_patterns/frozen_model"


def check(compiler):
    records = []
    with tempfile.TemporaryDirectory(prefix="ca2-call-trace-") as directory:
        work = Path(directory)
        events = work / "events"
        events.mkdir()
        for group in ("MEC_LII_Stellate", "CA3_Pyramidal", "CA2_Pyramidal", "CA2_Basket",
                      "CA2_Wide_Arbor_Basket", "CA2_Bistratified", "CA2_SP_SR"):
            (events / f"{group}.txt").write_text("0 0\n5 0\n")
        for variant in ("nominal", "sensitivity", "ca1_adequacy"):
            sources = ["circuit"] + (["baseline"] if variant == "nominal" else [])
            for source in sources:
                binaries = []
                for label, root in (("frozen", FROZEN), ("working", MODEL)):
                    binary = work / f"{label}-{variant}-{source}"
                    subprocess.run([compiler, "-std=c++11", "-I", str(ROOT / "tests/native_trace"),
                                    str(root / variant / "src" / f"{source}.cpp"), "-o", str(binary)],
                                   check=True, capture_output=True, text=True)
                    binaries.append(binary)
                if source == "baseline":
                    cases = [[mode, "17", "10", "20"] for mode in ("old", "fresh")]
                else:
                    base = ["17", "10", "20", str(events)]
                    cases = [[mode, *base] for mode in ("calibration", "core", "readout")]
                    cases += [["core", *base, "100", scope] for scope in ("all", "pyramidal")]
                    if variant == "sensitivity":
                        cases += [["readout", *base, "1", "all", "2"]]
                    if variant == "ca1_adequacy":
                        cases += [["readout", *base, "3", "all"]]
                for arguments in cases:
                    traces = [subprocess.check_output([str(binary), *arguments], text=True)
                              for binary in binaries]
                    if traces[0] != traces[1]:
                        raise AssertionError(f"API call trace changed: {variant}/{source} {arguments}")
                    records.append({"variant": variant, "harness": source,
                                    "arguments": ["<event_directory>" if arg == str(events) else arg
                                                  for arg in arguments],
                                    "calls": len(traces[0].splitlines()) - 1,
                                    "trace_sha256": hashlib.sha256(traces[0].encode()).hexdigest(),
                                    "identical": True})
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default="g++")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    results = check(args.compiler)
    if args.report:
        args.report.write_text(json.dumps({"scope": "Simulator API call equivalence using a recorder, not numerical or biological validation.",
                                          "cases": results}, indent=2) + "\n")
    print(f"Matched frozen and working API calls in {len(results)} cases; no GPU simulation performed.")
