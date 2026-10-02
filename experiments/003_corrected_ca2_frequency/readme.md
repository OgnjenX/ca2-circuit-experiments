# Corrected CA2 frequency-response assay

Experiment 003 replaces the defective simulator dynamics used in the historical
[experiment 002](../002_sun2021_ca2_frequency/ERRATUM.md). Historical outputs,
frozen scientific hashes, archives and backend identities remain preserved.

This version keeps the exported intrinsic parameters, synaptic conductance,
connection probability, delay, holding potential, target bands and calibration
and evaluation seeds. Receptor states now belong to individual synapses, with
exact exponential decay and TM recovery on a 1 ms arrival-event clock. CPU and
GPU conductance readbacks pass a prospectively specified, independently authored
float64 analytical oracle. The neuron RK steps do not refine the synaptic clock.

Three focused models are compared: exported STP, static release with identical
first impulse and receptor kinetics, and generic linear summation constructed
only from calibration single-pulse voltage responses. The linear kernel has
100 ms support and is zero beyond that interval; it is an approximation, with
no train-response fitting. Calibration changed recruitment only. All scientific
code and parameters were committed before held-out train testing.

[The report](report.md) gives actual outcomes, numerical sensitivity, exclusions,
comparison with historical results and the remaining scientific limits.
[Reproduction instructions](reproduce.md) describe the separate source patch,
raw archive and validation. A complete run includes 120 exported-STP and 120
matched-static tests, with 60 numerical pairs in total. Every raw monitor is
reread before scoring. Missing or duplicate coverage, ineligible primary runs
and failed numerical gates prevent setup success.

The assay remains a reduced somatic direct-input model. A match with conservative
bands is conditional compatibility, not biological validation. Neither this
assay nor the historical benchmark establishes CA2 function or invalidates the
usefulness of Hippocampome as a source for hypotheses.
