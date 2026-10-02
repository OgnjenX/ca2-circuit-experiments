# Bounded pre-reset drift diagnostic

This is a separately authorized post-hoc engineering diagnostic, committed before its new integrations. It uses one retained actual GPU trace, at 100 pA and 80 substeps/ms, and stops before its first reset. It neither replaces the original spike/reset verification nor waives its failed gates.

The frozen protocol, independent review and checksum manifest define five variants, exact stimulus transitions, all per-substep states, a common pre-threshold comparison window, and descriptive drift telemetry. The explicit float32 implementation does not claim to reproduce compiled GPU FMA/rounding exactly. Coefficient sensitivity changes three constants jointly.

Run from the repository root, with the pinned Python requirements installed and the original raw archive extracted to its recorded workspace:

```sh
python experiments/003_whitebirch_intrinsic/addenda/004_prefix_diagnostic/prefix.py \
  --native-trace data/workspaces/003-whitebirch-gpu-pre-freeze-v7/traces/rk80_step100.csv \
  --output data/workspaces/003-whitebirch-prefix-diagnostic-v1 \
  --frozen-diagnostic-commit "$(git log -1 --format=%H -- experiments/003_whitebirch_intrinsic/addenda/004_prefix_diagnostic/preregistration_manifest.json)"
```

The output directory must be fresh. The runner checks both the new committed freeze and the original scientific freeze before integration. The original archive remains unchanged; new per-substep CSV files are retained in a separately named diagnostic archive. Compact results and interpretation are linked here after execution.
