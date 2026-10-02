"""Check one fresh GPU core trial and its three matched output controls."""
import argparse
import json
from pathlib import Path
import subprocess
from _common import ROOT
from ca2lab.provenance import verify_frozen, sha256
from ca2lab.monitors import read_spikes, read_voltage
from ca2lab.events import read_events, same_events

COUNTS = {"CA2_Pyramidal": 18956, "CA2_Basket": 105, "CA2_Wide_Arbor_Basket": 147,
          "CA2_Bistratified": 79, "CA2_SP_SR": 94, "MEC_LII_Stellate": 10818,
          "CA3_Pyramidal": 4096, "CA1_Pyramidal": 128, "CA1_Basket": 819, "CA1_Bistratified": 1962}
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("workspace", type=Path)
parser.add_argument("--output", type=Path, help="New directory for this smoke run; default: workspace/smoke")
args = parser.parse_args()
workspace = args.workspace.resolve()
verify_frozen(workspace)
plan = json.loads((workspace / "frozen-task-protocol.json").read_text())
trial = plan["stimulus_definition"]["trials"][0]
events = workspace / "stimuli/reset-task-v1" / trial["name"]
binary = workspace / plan["executable_path"]
smoke = args.output.resolve() if args.output else workspace / "smoke"
smoke.mkdir()  # Refuse an existing smoke run.
# Import the byte-preserved replay constructor, without executing batch runners.
import sys
sys.path.insert(0, str(workspace))
from replay_reset_trial import prepare
summaries = {}

def execute(name, mode, event_directory):
    directory = smoke / name
    (directory / "results").mkdir(parents=True)
    command = [str(binary), mode, str(trial["network_seed"]), "250", str(plan["substeps"]), str(event_directory), "100", "pyramidal"]
    (directory / "configuration.json").write_text(json.dumps({"command": command, "executable_sha256": sha256(binary)}, indent=2))
    with (directory / "run.log").open("w") as log:
        completed = subprocess.run(command, cwd=directory, stdout=log, stderr=subprocess.STDOUT)
    (directory / "exit-status.txt").write_text(str(completed.returncode))
    completed.check_returncode()
    results = directory / "results"
    spike_files = sorted(results.glob("spk_*.dat"))
    counts = {}
    for file in spike_files:
        population = file.stem.removeprefix("spk_")
        data = read_spikes(file, COUNTS[population], 250)
        counts[population] = len(data)
        input_file = event_directory / f"{population}.txt"
        if input_file.exists() and not same_events(data, read_events(input_file, COUNTS[population], 250)):
            raise ValueError(f"Delivered events differ: {population}")
    voltage_files = sorted(results.glob("n_*.dat"))
    expected = 5 if mode == "core" else 1
    if len(voltage_files) != expected or len(spike_files) != (7 if mode == "core" else 9):
        raise ValueError("Missing population monitor")
    for file in voltage_files:
        read_voltage(file, COUNTS[file.stem.removeprefix("n_")], 250)
    summaries[name] = counts
    print(f"Verified {name}: {counts}", flush=True)
    return directory

core = execute("core", "core", events)
prepare(core, smoke / "replays", trial["name"])
for condition in ("intact", "blocked", "scrambled"):
    execute(condition, "readout", smoke / "replays" / condition)
(smoke / "verification.json").write_text(json.dumps({"trial": trial["name"], "spike_counts": summaries,
    "checks": ["frozen artifact hashes", "exit status", "input delivery", "spike bounds and duplicates", "complete finite voltage records"],
    "scope": "One fresh trial and three output controls; not a full study replication"}, indent=2))
