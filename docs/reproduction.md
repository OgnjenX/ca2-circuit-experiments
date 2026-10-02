# Reproducing experiment 001

There are three distinct activities: checking the published reference results,
reanalyzing the recorded raw data, and running a fresh simulation. A successful
file check is not biological validation.

## Inspect the reference results

Install the package as shown in `readme.md`, then run:

```sh
python scripts/verify_repository.py
```

This checks the published files and source map against recorded checksums, the
frozen plans, trial coverage, controls and result summaries. It does not rerun the
GPU simulation or independently reanalyze every raw record.

## Run a fresh simulation

Use a Linux machine with a CUDA-compatible NVIDIA GPU. The archived binaries
target sm_86; the original machine was an RTX 3050 Ti laptop GPU. Install the
CUDA 12 runtime and cuRAND 10 libraries. The build environment used CUDA 12.4 and
g++ 12. A different architecture or rebuild requires renewed numerical checks.

```sh
python -m pip install -e '.[report]'
python scripts/fetch_artifacts.py runtime
python scripts/prepare_workspace.py data/workspaces/experiment_001
python scripts/smoke_run.py data/workspaces/experiment_001
python scripts/reproduce.py data/workspaces/experiment_001 --phase gpu
python scripts/reproduce.py data/workspaces/experiment_001 --phase analysis
```

The preparation command refuses an existing destination. It verifies the runtime
asset and all 14 frozen artifacts. Historical calibration evidence is retained;
fresh task results and completion markers are absent. The smoke run uses a
separate directory and checks one core trial with all three output controls.

The full GPU phase runs the nominal task, parameter sensitivities, numerical
sensitivities and unseen-input tests sequentially. It can take hours. Do not
launch overlapping GPU batches. An unfinished existing run must be inspected
before attempting recovery; the runners refuse to overwrite it.

The analysis phase uses `analyze_reset_task_v2.py`. The frozen v1 script contains
a documented path-variable collision and remains preserved for provenance.
Feature definitions, splits and classifier rules were unchanged by the fix.

The runtime bundle includes the original analysis dependencies used for plots.
The analysis interpreter used NumPy 2.3.5; ReportLab 4.4.9 and Pillow 12.3.0
produced the report. Package versions for inspection are pinned separately.

## Recover the original records

```sh
python scripts/fetch_artifacts.py recorded
python scripts/prepare_recorded.py data/recorded/experiment_001
```

This restores `ca2-experiment/` and its companion upstream source archive.
It preserves the original filenames, checksums and logs. Some configurations
contain original absolute paths. Inspect the records as archived; do not change
them to satisfy a relocated path assertion. For a fresh run, use the workspace
commands above. The original `completion-audit.json` documents what was verified
at the time of the study, including the limits of aggregate graph signatures.

## Compare results

Compare per-network scores, paired effects, response counts and numerical-check
outcomes with `experiments/001_input_patterns/reference/`. Timestamps, process
IDs and absolute paths will differ. Retain the failed gain-150 precision check
and the CA1 adequacy limitation even if a new build behaves differently.

The repository reorganization is not a second full simulation replication.
Repository checks, artifact round trips and a GPU smoke run are reported
separately from the original study's validation.
