# Independent dynamics validation

`spec.json` declares methods, timing, cases and tolerances. `oracle.py` is an
independent float64 analytical impulse convolution and TM event recurrence;
it does not import the repaired backend. `probe.cpp` reads actual public
CARLsim conductances, and `run.py` compares CPU and GPU against that oracle.
The final 38 cases cover 0/1/31/91/255 silent afferents; homogeneous and
heterogeneous summed impulses; all four E/I receptors; static, STP and mixed
release; rise/decay mode mixtures; paired-pulse/recovery; delay 1/5; events at
0/999/1000/1001; new-network reset; and outgoing connections configured in both
orders, including repeated enable/disable and the short disable overload.
There is no supported full-network reset API in this backend; reset validation
constructs a fresh network and reproduces the original impulse.

The first spec/oracle commit is `fd90779`, before repaired biology. Development
then clarified readback timestamps from the dispatch code: delay 1 uses tD=0,
so the readback after integration tick t observes emission+delay−1. The initial
callback skipped a pulse at t=0; its scheduling state was repaired. These
validation-only revisions were committed with the final implementation before
calibration and the exact biological freeze. No biological train was used to
set these methods or tolerances. The tolerated error is 2e−5 absolute plus
1e−4 relative. All final errors are far smaller (maximum 1.8416423937933635e−8).

`evidence/corrected.json` records the final independently passing suite and
library hash. Development failures are preserved separately; earlier incomplete
attempt 2 was interrupted after diagnosing another missing POSIX worker return.
The historical CPU worker crash and GPU mixed-order suppression are real
backend defects. Historical-order1 isolates repeated aggregate decay: retention
is about 0.791 for one incoming edge and 4.37e−10 for 92 edges, despite only one
active afferent. Uninitialized historical slow-rise channels additionally
produce nonfinite values; their diagnostic error fields are stored as strings.

The final backend has one set of eight receptor states per incoming synapse
(32 extra bytes per edge). Each synapse decays with its own constants and each
neuron receives the sum. Neuron-wide receptor arrays remain public readback
and current-integration sums. Instantaneous and rising slow components can
coexist. Static release contributes events, retains its kinetics and shares
the first STP impulse amplitude. Configuration flags are keyed by connection,
with presynaptic-group flags retained only as a summary. POSIX CPU workers now
return defined values, and their per-synapse arrays use incoming-edge sizes.

The numerical change is explicit: receptor decay and TM recovery now use exact
exponentials at the 1 ms synaptic clock. For tau=4.7886 ms, v2 retains about
0.8115 in one tick, compared with the intended historical Euler factor 0.7912.
It does not silently claim to be the recorded solver. TM events use recovered
u and x, update u, release u*x/U, then deplete x. The published fitting utility's
biological g convention supports retaining the 1/U first-response normalization.
CPU/GPU agreement is secondary to the independent expectation. Passing these
finite cases establishes tested numerical behavior, not all backend features
or biological validity.

A separately labeled post-outcome archived-binary diagnostic directly links the
original nominal library with recorded SHA aeb6838ecde6859f50ddcce09975c85f2d9f72bfd0680ccc2a2741df3ef9345d.
It reproduces the same silent-afferent GPU decay and CPU crash; raw GPU trace
hashes match the earlier verified-source rebuild. See
`evidence/archived_binary_diagnostic.json`. This confirms original binary
behavior while preserving the different identity of the reconstructed build.
