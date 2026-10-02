# Direct-input CA2 slice assay

This native harness supports experiment 002. It isolates the archived
MEC LII stellate → CA2 pyramidal connection and preserves its exported intrinsic
and synaptic parameters. There is no recurrent pathway, inhibition or NMDA
conductance. Prescribed synchronous input events approximate electrical input
trains; input neurons are spike generators, not integrated entorhinal cells.

The experiment controller generates `slice_config.h` directly from the two
archived CSV files and builds against the recorded nominal CARLsim4 library.
The exact generated header, executable, compiler command and checksums are in
the experiment's frozen record and raw workspace archive.

Usage:

```text
assay seed active duration_ms steps pulse_file holding_pA
```

The holding current is applied after network setup; warmup lasts 4,950 ms. Voltage
and spike monitors cover all 128 target cells. This backend writes voltage to
disk during warmup; analysis validates the full recording and then selects the
assay interval. A run must use its own results directory. The controller performs
input delivery and scientific eligibility checks after native completion.
