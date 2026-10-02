# Sun 2021 CA2 frequency-response benchmark

This experiment asks whether the existing Hippocampome-derived CA2 point model
reproduces the increase in the fifth versus first somatic EPSP during five-pulse
perforant-path trains, in the CA2 APV arm of Figure 5H in
[Sun et al. (2021)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8482869/).
It tests a published biological response before using the model for new predictions.

## Scope fixed before testing

The slice experiment used young mice, current-clamp holding near −70 mV, and GABA
receptor blockade. The selected arm also blocked NMDA receptors. Our reduced
assay contains 128 exported CA2 pyramidal point cells and the existing prescribed
MEC LII stellate input pool, with no inhibition, recurrence or NMDA current.
Intrinsic parameters, synaptic conductance, connection probability, delay and
short-term plasticity remain those in the archived Hippocampome exports. Source
spikes are imposed; an entorhinal network is not being simulated.

Only afferent recruitment is calibrated, using single pulses and seeds 101–102.
Five-pulse responses are held out. Three weak operating levels (1.44, 1.76 and
2.08 mV) are predeclared sensitivity scenarios. They use the Figure 4 CA2 weak
first EPSP mean ± SEM as an **unverified transfer to Figure 5's APV arm**. That
arm's absolute initial amplitude was not recovered. These scenarios are neither
an established APV amplitude range nor three groups of animals.

The primary comparison is EPSP5/EPSP1 at 30 and 50 Hz, evaluated with new network
seeds 201–205. Other frequencies provide descriptive context. Published means
and conservative uncertainty bands are digitized from the public graph;
there are no raw animal recordings in this experiment. A match must meet both
primary frequencies, remain subthreshold, and pass the declared numerical checks.
An agreement is conditional compatibility, rather than full-paper replication.
A mismatch is evidence about this implementation and these setups, rather than
proof that every possible Hippocampome-based model must fail.

The baseline convention is inferred from the paper's normalized traces. We also
report a pre-pulse incremental convention as a diagnostic without replacing the
primary metric. We cannot claim CA1 versus CA2 differences, the effect of adding
NMDA receptors, naturalistic spike replay, behavior, or CA2's function from this
assay. Exact naturalistic input timestamps were not recovered and are not invented.

## Prospective record

- `protocol.json`: fixed inputs, allowed calibration, held-out endpoints and gates.
- `source_targets.json`: source image identity, extraction coordinates and uncertainty.
- `source_audit.json`: exporter provenance and remaining source gaps. The export's
  default flag refers to connection-probability fallback, not automatically to
  generic synaptic dynamics. Database ancestry of the dynamics remains unverified.
- `frozen_configuration.json`: calibration, exact generated configuration and
  simulator identity, plus hashes checked before every test run and analysis.
- `setup_attempts.json`: retained recording-reader failure and its software repair.

Commit history separates the prospective plan, software repair, analysis freeze,
and outcomes. We do not retune the model after observing train responses.

## Running

Use a Python environment with NumPy and the recorded CARLsim4 backend described
in `simulators/carlsim4/source.json`, with a compatible NVIDIA GPU and CUDA runtime.
From the repository root, before this experiment has been frozen:

```sh
python experiments/002_sun2021_ca2_frequency/experiment.py build \
  --workspace data/workspaces/experiment_002 --backend /path/to/recorded/backend
python experiments/002_sun2021_ca2_frequency/experiment.py calibrate \
  --workspace data/workspaces/experiment_002
python experiments/002_sun2021_ca2_frequency/experiment.py freeze \
  --workspace data/workspaces/experiment_002
# Commit frozen_configuration.json before executing the held-out trains.
python experiments/002_sun2021_ca2_frequency/experiment.py run \
  --workspace data/workspaces/experiment_002
python experiments/002_sun2021_ca2_frequency/analyze.py \
  --workspace data/workspaces/experiment_002
```

A published, frozen experiment should be reproduced from its archived workspace
and configuration. A new calibration or different executable is a new protocol
revision, not a replacement for this record. The controller refuses overwritten
calibration, incomplete earlier runs, and changed frozen scientific files.

Results and archive instructions will accompany the completed record.
