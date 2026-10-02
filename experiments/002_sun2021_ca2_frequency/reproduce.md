# Reproduce the recorded CA2 benchmark

All commands start at the repository root on this experiment's branch/tag.
Use Python 3.12+ with NumPy. `pip install -e .` installs the shared analysis
package. No GPU is needed to verify or analyze recorded data. Figure generation
also requires Matplotlib; the recorded figure runtime used Matplotlib 3.11.2.

## Check the compact record

```sh
python experiments/002_sun2021_ca2_frequency/verify_evidence.py
python -m unittest discover -s tests -v
python scripts/verify_repository.py
```

The first command checks frozen scientific sources, artifact hashes, coverage
and consistency of the published comparisons. The last checks the preserved
experiment-001 record; it is not a biological-validation test for experiment 002.

## Download and recover the full raw data

The archive contains the original native executable, generated header and build
identity, calibration, all 120 tests, pulse files, logs, raw neuron/spike
recordings, and the retained single-pulse reader failure. The compressed file is
approximately 220 MB and expands to approximately 1.9 GB. The original copyrighted
paper figure is external and is not redistributed in the archive.

```sh
gh release download experiment-002-v1 --repo OgnjenX/ca2-circuit-experiments \
  --pattern experiment_002_recorded.tar.gz --dir data/downloads
python experiments/002_sun2021_ca2_frequency/restore_workspace.py \
  --archive data/downloads/experiment_002_recorded.tar.gz \
  --destination data/recorded/sun2021
```

`restore_workspace.py` checks the published archive size and SHA-256, rejects
unsafe archive members, extracts into a new directory, checks every recovered
file against the workspace manifest, and verifies the original frozen executable
and generated configuration. It refuses an existing destination.

## Re-analyze the raw monitors

```sh
python experiments/002_sun2021_ca2_frequency/analyze.py \
  --workspace data/recorded/sun2021/experiment_002
python experiments/002_sun2021_ca2_frequency/review_diagnostics.py \
  --workspace data/recorded/sun2021/experiment_002
python experiments/002_sun2021_ca2_frequency/plot_figures.py
```

The frozen analysis independently reads every test voltage and spike file,
verifies prescribed input delivery and checksums, recomputes measurements and
scoring, and rewrites the compact evidence. The later descriptive audit documents
exclusions and the limits of the numerical checks without changing scores.
`plot_figures.py` draws the PNG/SVG figures from that compact evidence. SVG text
or rendering metadata can differ across Matplotlib environments; that does not
change the scientific measurements. Exact frozen scientific sources must remain
unchanged to run the analysis.

## Execute fresh GPU runs with the frozen model

The original executable targets sm86 and depends on the CUDA 12 runtime
(`libcudart.so.12`, `libcurand.so.10`), standard C++ libraries and a functioning
NVIDIA driver. It ran on an RTX 3050 Ti Laptop GPU with driver 580.178.04 and
CUDA toolkit 12.4. A different GPU architecture or rebuilt executable is a new
execution record and requires an explicitly revised frozen identity; it must not
silently replace this experiment.

Keep the recovered raw data untouched and prepare a new workspace containing
only the frozen build and calibration. Do not rerun calibration:

```sh
python - <<'PY'
from pathlib import Path
import shutil
source = Path('data/recorded/sun2021/experiment_002')
target = Path('data/workspaces/experiment_002_replay')
target.mkdir(parents=True, exist_ok=False)
shutil.copytree(source / 'build', target / 'build')
shutil.copy2(source / 'calibration.json', target / 'calibration.json')
PY
python experiments/002_sun2021_ca2_frequency/experiment.py run \
  --workspace data/workspaces/experiment_002_replay
```

Each run uses a fresh process, the original seeds, afferent recruitment and
schedules, and an isolated results directory. The controller checks all frozen
scientific sources and the original executable before running. The nominal
library is statically linked into the executable, so the complete simulator
source is not required to execute it. The older experiment's runtime/source
release and `simulators/carlsim4/source.json` retain the backend source/build
record if a separate rebuild is needed.

Analysis of a replay rewrites the experiment's evidence with that replay's
provenance and raw checksums. To preserve the published record while comparing a
fresh replay, perform that analysis in a separate checkout/worktree and retain
the earlier record. New calibration, different drug conditions or model tuning
require a new protocol revision with a new held-out test; they are not
post-outcome repairs of this result.
