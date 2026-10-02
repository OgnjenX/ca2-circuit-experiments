# Backend dynamics erratum — 2 October 2026

The biological interpretation of experiment 002 is invalid pending corrected
synaptic dynamics. Its frozen files, source hashes, raw archive, executable
identities and reported measurements remain historical evidence and have not
been replaced. Numerical agreement between RK substep settings did not detect
the synaptic defect because both settings used the same 1 ms synaptic clock.

In the recorded CARLsim4 backend, a cell-wide receptor state is decayed once
for every incoming synapse. Consequently silent afferents change the response
of an active synapse, and heterogeneous connections cannot retain their own
time constants. Independent GPU impulse readbacks reproduce this failure.
The CPU source has the same aggregate-state defect, and its optimized worker
routines additionally exhibit undefined behavior from missing return values.
Mixed STP configuration calls can suppress GPU events; static GPU events were
also omitted. Receptor kinetics were initialized only inside STP enable paths.

Experiment 001 shares this backend and its physiological/functional conclusions
require revalidation. Repeating its full experiment is outside this repair.
The database's usefulness is a separate question from simulator correctness.

The separately versioned `synapse_dynamics_v2.patch` and experiment
[003](../003_corrected_ca2_frequency/readme.md) contain the correction,
independent oracle validation and prospective controls. The new backend uses
exact exponential decay and recovery on the declared 1 ms arrival-event clock,
rather than preserving the historical Euler discretization. The first impulse
normalization by 1/U remains: the fitting utility describes biological g as
fitted g times U. This normalization is not itself evidence of a defect.

Historical results must not be cited as evidence that Hippocampome fails (or
validates) CA2 biology. Even corrected agreement with broad digitized bands
would be conditional compatibility under unresolved assay/provenance assumptions.
