# CA2 point-neuron circuit

These are the readable working sources. `nominal/` is the experiment 001 circuit;
`sensitivity/` adds the output-strength variants; `ca1_adequacy/` is the separate
downstream check. Formatting uses the repository's `.clang-format` settings.

Exact pre-format sources remain under
[`experiments/001_input_patterns/frozen_model/`](../../experiments/001_input_patterns/frozen_model/readme.md).
The source map points to those copies, and the original runtime bundle is unchanged.
The working sources initially contain the same C++ tokens as those frozen copies.
Configuration fragments have since been wrapped in ordinary functions for IDE
analysis. The function bodies keep the original statements and parameters; API
call comparisons cover the harness modes and gain controls. New scientific
changes need a model revision and renewed numerical checks.

The root CMake project builds the working sources against the recorded backend
into `build/development/`. These development executables are separate from the
frozen binaries and are not accepted automatically by the frozen experiment runner.
See [development](../../docs/development.md) for IDE setup and build commands.

Source records and parameter tables are linked in
[model provenance](../../docs/model_provenance.md). The native code derives from
CARLsim; see [its license](../../licenses/carlsim4.txt).
