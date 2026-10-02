"""Check the migration and compact reference evidence without claiming a rerun."""
import json
from _common import ROOT, index
from ca2lab.provenance import verify_file

experiment = ROOT / "experiments/001_input_patterns"
reference = experiment / "reference"
source_map = json.loads((experiment / "provenance/source_map.json").read_text())
for entry in source_map.values():
    verify_file(ROOT / entry["repository_path"], entry["sha256"])
manifest = json.loads((reference / "artifact-manifest.json").read_text())
checked_reference = 0
for file in reference.glob("*.json"):
    if file.name in manifest["files"]:
        recorded = manifest["files"][file.name]
        verify_file(file, recorded["sha256"], recorded["bytes"])
        checked_reference += 1
plan = json.loads((reference / "frozen-task-protocol.json").read_text())
results = json.loads((reference / "reset-task-results.json").read_text())
if len(plan["files_sha256"]) != 14 or len(plan["stimulus_definition"]["trials"]) != 80:
    raise ValueError("Unexpected frozen plan coverage")
if len(results["trials"]) != 240 or len(results["per_seed_context_condition"]) != 30:
    raise ValueError("Unexpected nominal result coverage")
for row in results["per_seed_primary_accuracy"]:
    if any(row[condition] != 0.5 for condition in ("intact", "blocked", "scrambled")):
        raise ValueError("Primary summary differs from reported result")
precision = json.loads((reference / "variant-precision-results.json").read_text())
if len(precision["results"]) != 8 or sum(not row["pass"] for row in precision["results"]) != 1:
    raise ValueError("Numerical limitation missing from reference")
for asset in index()["assets"].values():
    if len(asset["sha256"]) != 64 or asset["bytes"] <= 0:
        raise ValueError("Incomplete release asset index")
snapshot = json.loads((experiment / "provenance/repository_files.json").read_text())
for path, digest in snapshot.items():
    if path.endswith(".md") and path != path.lower():
        raise ValueError(f"Markdown filename must be lowercase: {path}")
    verify_file(ROOT / path, digest)
print(f"Verified {len(source_map)} preserved source/parameter files, {checked_reference} reference files, "
      f"{len(snapshot)} repository files, 80 nominal trials and the retained precision failure.")
print("This is repository integrity and reference consistency, not biological validation or a full rerun.")
