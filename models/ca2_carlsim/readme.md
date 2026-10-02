# CA2 point-neuron circuit

`nominal/` holds the frozen circuit source and configurations used in experiment
001. `sensitivity/` adds an optional multiplier for three default-flagged CA2
pyramidal output connections. `ca1_adequacy/` is the separate downstream check.

These files are exact source copies. The fresh-run bundle restores their original
paths and contains the recorded binaries. Editing a shared model for a future
study requires a new model version and renewed numerical and biological checks.

Source records and parameter tables are linked in `../../docs/model_provenance.md`.
The native code derives from the CARLsim framework; see `../../licenses/carlsim4.txt`.
