# CA2 circuit experiments

Controlled simulations of hippocampal CA2, with explicit model assumptions,
frozen experiment plans, and recorded validation results.

The first study asks whether CA2 pyramidal output helps distinguish two synthetic
cortical input patterns in a downstream CA1 population. It uses Hippocampome
parameters and CARLsim4. It does not model a recorded behavioral task or establish
a function of CA2 in animals.

## Start here

- [Experiment 001](experiments/001_input_patterns/readme.md): question, controls and findings.
- [Reproduction](docs/reproduction.md): inspect the results, recover the recorded run, or run a fresh experiment.
- [Model provenance](docs/model_provenance.md): measured ingredients, defaults, fits and validation limits.
- [Development](docs/development.md): CLion, Python environment, formatting and CMake targets.
- [Repository layout](docs/repository_layout.md): where code, plans and data belong.
- [Migration checks](docs/migration_checks.md): what was tested while packaging this repository.
- [New experiments](docs/experiment_workflow.md): how to add a study without changing an existing record.

## Results from experiment 001

The primary CA1 spike-count classifier stayed at 50% across all five networks and
all output conditions. CA3 input coincided with strong CA2 pyramidal suppression,
but halving the fitted inhibitory strength reversed this effect in the sensitivity
network. Some information was available in CA1 voltage; its dependence on output
alignment, inputs and numerical settings is reported separately.

One numerical spot check failed. The downstream CA1 assay did not establish
matched biological validation. These limitations are part of the result.

## Check the repository

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python scripts/verify_repository.py
python -m unittest discover -s tests
```

Python 3.12 or newer is required. Inspection and analysis checks do not need a GPU.
The original executable targets NVIDIA sm_86 and needs CUDA 12 runtime libraries.

The original raw records and a fresh-run runtime bundle are release assets, kept
out of Git. Each asset has a SHA-256 checksum in [the archive index](artifacts/experiment_001.json).
The archived experiment scripts are preserved byte-for-byte; their compact style
and historical filenames are not the convention for new code.

## Scientific status correction

The recorded backend used by experiments 001 and 002 has a reproduced synaptic
dynamics defect. Their biological interpretations require revalidation. See
[the erratum](docs/synapse_dynamics_erratum.md) and the separately versioned
[corrected experiment 003](experiments/003_corrected_ca2_frequency/readme.md).
