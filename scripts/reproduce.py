"""Run the archived experiment sequentially in a prepared workspace."""
import argparse
from pathlib import Path
import subprocess
import sys
from _common import ROOT
from ca2lab.provenance import verify_frozen

GPU = ["run_reset_task.py", "run_sensitivities.py", "run_numerical_sensitivity.py", "run_generalization.py"]
ANALYSIS = ["analyze_reset_task_v2.py", "analyze_secondary_voltage.py", "audit_nominal_experiment.py",
            "analyze_response_dynamics.py", "analyze_sensitivity_results.py", "audit_generalization_inputs.py",
            "analyze_generalization.py", "plot_final_results.py", "plot_response_dynamics.py", "build_scientific_report.py"]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("workspace", type=Path)
parser.add_argument("--phase", choices=["gpu", "analysis"], required=True)
args = parser.parse_args()
workspace = args.workspace.resolve()
verify_frozen(workspace)
if args.phase == "analysis" and not (workspace / "generalization-execution-complete.json").exists():
    raise ValueError("Complete the GPU phase before analysis")
for name in GPU if args.phase == "gpu" else ANALYSIS:
    print(f"Running {name}", flush=True)
    subprocess.run([sys.executable, str(workspace / name)], cwd=workspace, check=True)
