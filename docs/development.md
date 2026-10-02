# Development setup

CLion is a good fit for this repository's C++ harnesses and Python analysis tools.
Its bundled Python plugin supports completion and run/debug configurations;
VS Code is also usable, but is not required for the mixed-language project.
See [CLion Python support](https://www.jetbrains.com/help/clion/python.html).

## Open the project

Open the repository root in CLion as a CMake project. Import the `development`
preset when prompted. It uses g++ 12, CUDA libraries from the installed toolkit,
and the recorded CARLsim backend in the prepared runtime workspace. The CMake
project produces a compilation database for code completion and navigation.

Create the Python environment and restore the runtime on another machine:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[report]'
python scripts/fetch_artifacts.py runtime
python scripts/prepare_workspace.py data/workspaces/experiment_001
```

Choose `.venv/bin/python` in CLion's Python Interpreter settings. The local setup
already registers this environment. Machine-specific interpreter and window
settings remain in ignored `.idea/` files. Shared run configurations live in `.run/`:
`Repository checks` and `Shared Python tests`. The latter uses unittest discovery.

## Build and check

```sh
cmake --preset development
cmake --build --preset development
ctest --preset development
```

The four native targets are `ca2_nominal`, `ca2_sensitivity`, `ca1_adequacy`, and
`ca2_baseline`. CTest runs repository integrity and Python checks. It does not
launch GPU simulations. Native run arguments and an isolated results directory
must be chosen for the particular experiment; running a binary without arguments
prints its usage. Use the archived reproduction workflow for experiment 001.

On a machine without CUDA or the runtime bundle, configure Python checks only:

```sh
cmake -S . -B build/python -DCA2_BUILD_MODELS=OFF -DPython3_EXECUTABLE="$PWD/.venv/bin/python"
ctest --test-dir build/python --output-on-failure
```

The CMake build compiles the C++ harnesses against the existing CUDA backend;
it does not recompile the simulator kernels. `scripts/rebuild_backend.py` handles
that separate rebuild. Debug symbols in a harness do not add GPU debug symbols
to the recorded backend.

## Formatting and scientific provenance

Use clang-format with the root `.clang-format` file for editable files under
`models/ca2_carlsim/`. The local formatter is bundled with CLion. Enable clang-format
in Settings | Editor | Code Style | C/C++ if it is not already selected.

The original compact native sources remain in experiment 001's `frozen_model/`.
Their source hashes and the release assets retain the historical experiment
record. The initial cleanup verifies that working and frozen sources have the
same C++ token sequence. Include order and string literals are preserved.
Changes to scientific logic or parameters require a new experiment/model revision.
