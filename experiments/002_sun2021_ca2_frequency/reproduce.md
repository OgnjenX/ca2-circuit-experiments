# Reproduce the corrected revision of experiment 002

The corrected revision retains the original run identity `experiment_003` and
release `experiment-003-v1`. Download the main and diagnostic archives using
[evidence/archive.json](evidence/archive.json) and
[evidence/diagnostics_archive.json](evidence/diagnostics_archive.json); verify
bytes and SHA-256 before extraction. Do not overwrite another workspace.

Install dependencies (`python -m pip install -e .`) and use a full Git clone.
Shallow clones must fetch the immutable snapshot commit
`81cbbb7ad130c4575713b99dba96b2743ecb5650` first. All hosted evidence jobs fetch
full history. Verify compact evidence without a GPU:

```sh
python experiments/002_sun2021_ca2_frequency/verify_evidence.py
```

Frozen scripts and manifests embed their original experiment paths. Use the
compatibility runner, which restores the pinned tracked tree temporarily and
exports analysis evidence to a new directory. Pass absolute workspace paths:

```sh
python scripts/run_frozen_assay.py --output /new/path/reanalysis -- \
  --workspace /path/to/extracted/experiment_003
python scripts/run_frozen_assay.py --script diagnostics/pair_diagnosis.py \
  --output /new/path/pair-diagnostic -- \
  --workspace /path/to/extracted/experiment_003
```

The published main archive already includes the categorical metadata repair and
retained original measurements. Do not apply that adapter twice. See
[METADATA_ERRATUM.md](METADATA_ERRATUM.md). The unchanged frozen analysis checks
scientific identity and rereads the raw monitors before scoring. Generated
compact outputs go to the requested new directory, never the canonical record.
Direct invocation of the relocated frozen controller/analyzer cannot resolve
its historical paths; use this runner or the pinned snapshot checkout.

The [original reproduction instructions](https://github.com/OgnjenX/ca2-circuit-experiments/blob/81cbbb7ad130c4575713b99dba96b2743ecb5650/experiments/003_corrected_ca2_frequency/reproduce.md)
retain complete build and GPU diagnostic commands. The Lenovo run used a 4 GB
RTX 3050 Ti, sequential runs and a separately versioned backend. Different build
identities require renewed validation and a new scientific freeze. This
consolidation did not rerun simulations or tune the assay. A new experiment 003
must define a different question and freeze its plan prospectively.
