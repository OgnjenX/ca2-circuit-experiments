# Repository migration checks

The repository was packaged and checked on 2026-10-02. These checks concern
software recovery and a small reproduction test, rather than biological validity.

- The source map checks 79 preserved source and parameter files. The original
  inventory checks 62 compact reference files.
- The runtime archive was restored into a new directory and all 14 frozen
  artifacts matched. No completed task runs were present before testing.
- The recorded archive was restored and all 40,217 inventoried files matched
  their original sizes and SHA-256 checksums.
- Eight shared-code tests passed after an editable package install. They cover
  stimulus delivery, count-bin boundaries, train-only decoding, exact ties,
  malformed monitors, finite complete voltage records, hashes and extraction.
- Applying the backend patch recreated all 77 recorded source/build files.
  A separate CARLsim library and nominal circuit executable compiled and linked.
  Their hashes differ from the recorded binaries; numerical equivalence of the
  rebuild was not tested. Use the recorded runtime for the archived experiment.
- One fresh nominal trial (`seed31-ctx0-id0-rep0`) ran on the NVIDIA GPU, followed
  by intact, blocked and scrambled CA1 replays. All four processes completed;
  inputs were delivered exactly and monitors were complete and finite. All 42
  spike-event sets and monitored voltage arrays matched the corresponding
  original trial. Binary event ordering can differ, so spike comparisons use
  sorted time/cell pairs.

The study's complete GPU batch was not run again during packaging. The original
completion audit remains historical evidence. Exact migration outcomes are in
`../experiments/001_input_patterns/provenance/migration_checks.json`.
