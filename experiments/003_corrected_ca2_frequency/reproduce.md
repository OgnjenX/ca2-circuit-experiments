# Reproduce experiment 003

Use the repository commit referenced by the freeze and an NVIDIA GPU compatible
with the sm_86/PTX build. The Lenovo run used an RTX 3050 Ti with 4 GB VRAM,
CUDA nvcc and g++-12. All simulations ran sequentially. A sampled total GPU
memory reading was 250 MiB; this is an observed snapshot, not a measured peak.

Install the Python dependencies and put the checksum-verified upstream archive
specified by `artifacts/experiment_001.json` in `data/downloads`.

```sh
python scripts/rebuild_backend_v2.py /new/path/corrected-backend
python simulators/carlsim4/validation/run.py \
  --backend /new/path/corrected-backend/backend --output /new/path/validation
```

The builder first applies the historical patch and verifies all 77 original
source hashes. It then applies `synapse_dynamics_v2.patch` with zero fuzz and
verifies the new source hashes. Both versions are kept separate. The local
library hash is a recorded binary identity; different toolchain builds can
have different binary hashes and require a new experiment identity and renewed
validation, rather than changing this freeze.

The published archive includes the frozen assay and static executable,
configuration, corrected backend source/library/build log, calibration and
all 240 train runs with full raw monitors. Download its separately named asset
from the link in `evidence/archive.json`, verify its SHA-256 and bytes, and
extract it into a fresh directory. It must never replace experiment 002.

```sh
python experiments/003_corrected_ca2_frequency/verify_evidence.py
python experiments/003_corrected_ca2_frequency/analyze.py \
  --workspace /path/to/extracted/experiment_003
```

Before the analysis command on the original controller batch, run
`python experiments/003_corrected_ca2_frequency/finalize_metadata.py --workspace /path/to/extracted/experiment_003`.
Published archives already contain the adapted batch and its retained original;
do not run the adapter twice. See `METADATA_ERRATUM.md` for this categorical-only
software repair.

The analysis command rechecks the freeze and every raw monitor before repeating
scoring and constructing the calibration-only null. Published compact evidence
is covered by `evidence/manifest.json`. GPU regressions are separate from hosted
CI, which verifies historical integrity, complete corrected coverage and scoring
without launching a GPU simulator.

For a fresh study, copy the prospective controller/protocol to a new experiment
identity, then build, calibrate, freeze and commit before running trains. The
existing controller intentionally refuses changes to frozen scientific inputs,
incomplete earlier runs, or overwritten calibration. Recorded failures from
backend development are retained in the validation archive; they are not
biological calibration exclusions. Failed calibration candidates and all
ineligible train runs remain in this experiment's raw archive.
