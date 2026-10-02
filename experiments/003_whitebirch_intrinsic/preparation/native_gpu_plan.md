# Native GPU preparation (unexecuted)

`gpu_harness.cpp` uses actual `GPU_MODE` and `GPU_CORES`, one CA2 target, and the
unchanged corrected static library. A silent spike-generator group with a zero
weight connection satisfies native synapse allocation assumptions, following the
existing current-step diagnostic convention. It returns no spike times and adds
no target current. It is not a simulated biological sample.

The translation unit includes the original `interface/src/carlsim.cpp` read-only
with an access-control macro after standard headers. This exposes `sim._impl->snn_`
and `groupConfigMDMap` solely for initial-state setup and state observation. The
link map must show that the archive's `carlsim-cpp.o` was not selected; kernel and
CUDA code come from the existing library. This unsupported internal API requires
pinning the backend source/header hashes and library hash. No backend file or
historical binary is rewritten.

After `setupNetwork`, CUDA HostToDevice copies initialize only the target's
`voltage`, `nextVoltage`, `recovery`, `Izh_ref_c` and `curSpike` arrays to
`-70`, `-70`, `float(u_hold)`, `0`, `false`. Roundtrip DeviceToHost reads verify
them before any simulation call. A fresh simulator process is used per current
and timestep. Exact archived CSV parameter values and holding calculations are
cast to float32 at the native API boundary. Pulse current is computed as native
float32 holding bias plus native float32 step increment. Native stdout reports
the actual parameter arrays, initial recovery, bias, pulse, timestep, refractory
period, and compilation identities.

The linker wraps `cudaMemcpy`. It first calls the real copy. Only the original
DeviceToDevice `nextVoltage -> voltage` copy for the target partition triggers
observation; this occurs after each GPU neuron-state kernel/substep in
`globalStateUpdate_N_GPU`. The observer then reads target voltage, recovery,
refractory counter and `curSpike` through the real DeviceToHost API. No state is
written during observation. These added barriers serialize observation and may
change wall time; dynamics arithmetic/kernel code remains unchanged. Runtime
matching, sample count and clock checks must pass before a trace can be accepted.

CSV columns are `time_ms,v_mV,u_pA,ref_counter,curSpike`; an initial row at zero
precedes all substep-end rows. Time labels use the declared grid `ms+j/steps`;
stdout separately records actual float32 integration timestep. Reset events must
be inferred from prior voltage above threshold and prior zero refractory counter,
with reset state/counter confirmation, rather than counting sticky `curSpike`.
This observation route does not itself localize between-grid threshold crossings;
independent numerical analysis must handle and verify them explicitly.

Native command (execution is gated):

```
gpu_harness --run-frozen <20|40|80> <0..1000, increment 100> <fresh trace.csv>
```

`build_driver.py --workspace <fresh ignored workspace>` compiles only by default.
It records full compiler command, source/header/library/dependency hashes,
compiler and nvcc identities, executable hash and wrapper symbols. Execution
uses `--execute-existing --frozen-commit <HEAD>` with the already compiled frozen
workspace, committed source inputs, and
`revisions/002/verify_stages.py --require-numerical-ready --build-record <record>`.
The workspace build record must byte-match the committed revision record. Its
library, complete backend source/header map, executable, generated header,
harness and driver hashes must match the committed manifest runtime pins and
actual files before each native process. Linked dynamic dependency paths and
hashes are checked, and loader overrides are rejected. Each successful process's
configuration JSON is compared with the exact frozen float32 expectations. The native binary
rejects normal invocation; only the gated driver supplies its authorization and
header-checksum environment variables. Planned phases are 100 ms holding,
1000 ms holding plus step, then 100 ms holding; step zero is the holding-only
control. All three timestep refinements and eleven currents have separate files.
Native nonzero exits, stdout, stderr, partial trace and metadata discrepancies
are preserved in per-sweep files; execution stops on the first failure. A flushed
progress line is emitted after every completed native process.

Compilation is not a successful GPU simulation or numerical validation. Native
runtime allocation, wrapper matching, trace completeness, float32 holding drift,
reset/counter fidelity, convergence and independent-reference agreement remain
unverified until the committed preregistration gate opens.
