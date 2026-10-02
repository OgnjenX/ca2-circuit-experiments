# CARLsim4 backend

Experiment 001 uses upstream commit `11ea96f750d125e4dcfbf67231429204322fa1bd`
plus the changes in `patches/experiment_001.patch`. The exact original source ZIP
is a release asset with a checksum in `../../artifacts/experiment_001.json`.

The runtime bundle contains the recorded binaries, all three patched simulator
libraries and source/build files. Use it for the archived numerical result.
The patch is also provided for inspecting or rebuilding the source. A rebuild
is a new numerical implementation until convergence has been checked again.

The original build logs are in experiment 001's recorded archive. They record
CUDA 12.4, g++ 12, sm_86 plus compute_86 PTX, O3 and host fast-math. The nominal
library uses reversal magnitude 77.8; sensitivity libraries use 75 and 80.
CPU thread-wrapper warnings are retained. Only GPU execution was tested.

See `../../scripts/rebuild_backend.py` for a separate source rebuild. It never
overwrites a recorded library or a frozen experiment binary.
