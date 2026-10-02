# Experiment 003: amended execution protocol

This revision preserves the blocked first preregistration at commit `658ad99fdcddd83f375e252da9091c35d504b2f0`. The official publisher 500 dpi Figure 1 and methods are now available. Both extraction passes remain model blind. The hidden 100 pA mean has no point estimate: the primary ten-current comparison uses a conditional [0, 1.2] spikes/s interval, assuming the blue marker was drawn under the red occluder. All SEM endpoints remain missing. See `target_data.json`, the two recovery extraction records, and `preparation/source_recovery.json`.

The user selected the unchanged CARLsim GPU backend as primary, and immediate reset as a separate diagnostic. Exact archived CSV parameters remain unchanged. GPU initialization supplies the prescribed holding state and bias; read-only link instrumentation observes actual native substeps. The independent reference reproduces delayed detection, refractory freeze, and reset semantics using DOP853. Numerical gates are prerequisites for biological scoring. The immediate-reset diagnostic never replaces a failed primary. `protocol.json` fixes all criteria before either integration.

## Reproduce on the pinned Lenovo runtime

The manifest binds source, model, protocol, target, compiled executable, backend library/source and review. The compiled workspace is deliberately external to Git. Its absolute build paths and hashes are recorded; rebuilding elsewhere produces a new executable identity and requires a new reviewed freeze, rather than silently replacing the pinned artifact.

```sh
.venv-whitebirch/bin/python experiments/003_whitebirch_intrinsic/revisions/002/tests_unit.py
.venv-whitebirch/bin/python experiments/003_whitebirch_intrinsic/revisions/002/verify_stages.py --require-numerical-ready
.venv-whitebirch/bin/python experiments/003_whitebirch_intrinsic/preparation/build_driver.py --workspace data/workspaces/003-whitebirch-gpu-pre-freeze-v7 --execute-existing --frozen-commit <amended-freeze-commit>
.venv-whitebirch/bin/python experiments/003_whitebirch_intrinsic/revisions/002/numerics.py --workspace data/workspaces/003-whitebirch-gpu-pre-freeze-v7 --output data/workspaces/003-whitebirch-numerics-v1 --frozen-commit <amended-freeze-commit>
.venv-whitebirch/bin/python experiments/003_whitebirch_intrinsic/revisions/002/analyze.py --numerics data/workspaces/003-whitebirch-numerics-v1/numerical_checks.json --target experiments/003_whitebirch_intrinsic/revisions/002/target_data.json --diagnostic data/workspaces/003-whitebirch-numerics-v1/immediate_diagnostic.json --output data/workspaces/003-whitebirch-analysis-v1
```

Raw traces and reference files belong in ignored uniquely named workspaces; compact evidence and reports will be committed separately after execution. Failed gates must remain visible. `verify_stages.py` distinguishes source sufficiency, committed implementation, local pinned runtime, numerical validity and measurement comparability. Repository integrity and CI are separate checks, not scientific validation.

Controls are NON-PILO mice that received methylatropine, diazepam and levetiracetam (92 cells, 48 mice). This assay tests somatic firing counts only. Population biological validation is not established: no equivalence margin or cell/mouse covariance is available. No optimization, temperature correction, waveform claims or simulated biological variance is permitted.

The extraction B `source.path` records the original external recovery workspace path; the identical asset is stored in this experiment at `source/figure1_publisher_hires.jpg` and identified by checksum. The preserved `model_configuration.json` field `specified_hybrid_reset` records the original immediate-reset assumption, now used only for the diagnostic. Its `user_selected_semantics` field and this revision's protocol identify the actual GPU delayed-reset/refractory path as primary.
