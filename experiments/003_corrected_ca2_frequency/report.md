# Corrected CA2 assay: scientific status

The corrected experiment does **not establish biological compatibility** with
Sun 2021's CA2 APV frequency response. Every STP and static setup fails the
predeclared success gate. Spiking excludes primary EPSP comparisons, and the
neuron integration sensitivity gates fail. The independent synaptic impulse
regressions pass; that is evidence for the repaired dynamics in the tested
cases, not a biological validation or a fully converged neuronal benchmark.

## What changed

The recorded backend decayed one cell-wide conductance once per incoming
synapse. Independent historical GPU impulse readbacks give one-tick retention
of about 0.791 for one edge and 4.37e−10 for 92 edges with only one active
input. The static GPU event path was absent, mixed configuration calls could
suppress STP, and optimized CPU workers crashed from undefined return values.
The historical experiment 002 interpretation is invalid; experiment 001 shares
the backend and needs revalidation. Their original scientific files, hashes,
backend identities and raw archives remain intact.

The separately versioned v2 patch stores eight receptor states per synapse,
decays each with its own constants, and sums them for each neuron. It preserves
first-response 1/U normalization. Exact exponential receptor decay and TM
recovery replace the historical Euler discretization, explicitly declared in
the validation spec. The synaptic clock remains 1 ms; 20/40 RK substeps change
neuron integration only. For tau=4.7886 ms the corrected exponential retention
is about 0.8115; it is not silently equated with the historical Euler 0.7912.

All 38 actual CPU/GPU conductance cases pass an independent float64 analytical
oracle, with maximum absolute error about 1.4e−8 versus a predeclared tolerance
of 2e−5 + 1e−4 relative. Tests include silent afferents, heterogeneous and summed
inputs, E/I and all receptors, static/STP/mixed release, rise modes, paired pulses,
recovery, delays, boundary events, new-network reset and configuration order.
The final validation source and prospective controls were committed before
calibration. The calibrated configuration and unchanged analysis were then
committed at `b2714df` before held-out trains. Development failures are retained.

## Runs and controls

Only single-pulse recruitment was recalibrated, on seeds 101–102. Exported
intrinsic parameters, conductance, connection probability, delay and STP values
remain fixed. Target bands and the all-cell peak convention are unchanged from
experiment 002. Evaluation uses seeds 201–205, six frequencies, and paired
20/40 RK settings at 30/50 Hz. No train-outcome tuning was performed.

| Target single EPSP (mV) | Historical active inputs | Corrected active inputs | Corrected calibration mean (mV) |
|---:|---:|---:|---:|
| 1.44 | 1859 | 443 | 1.4130 |
| 1.76 | 2281 | 559 | 1.7570 |
| 2.08 | 2704 | 654 | 2.0868 |

All 240 trains were run sequentially on the 4 GB RTX 3050 Ti. Native train wall time totaled 792.8 s. The static model uses identical kinetics and input recruitment but release=1. Its largest matched first-peak population-mean difference from STP is 0 mV. The linear null superposes calibration-only per-cell single-pulse kernels; it has 100 ms support, zero thereafter, and no train fit. It is a generic temporal-summation control, not a new validated neuron model.

| Model | Train runs | Eligible runs | Passing numerical pairs | Setup passes |
|---|---:|---:|---:|---:|
| stp | 120 | 56 | 3/30 | 0/3 |
| static | 120 | 46 | 2/30 | 0/3 |

The 102 eligible runs are mostly at lower frequencies. Every primary setup
contains excluded runs; all nominal 50 Hz runs spike in both models. Eligibility,
complete coverage and numerical pass are all required for setup success.
The categorical release label omitted by the frozen controller's measurement
rows was recovered one-to-one from verified run configurations and executable
hashes. The original batch is retained, and numerical fields are unchanged;
see `METADATA_ERRATUM.md` and `evidence/metadata_mapping.json`.

## Comparison and effect sizes

The table reports population means of the original per-cell fifth/first metric.
**Corrected STP/static numbers include spiking, ineligible traces and are
monitor-statistic diagnostics, not scored biological EPSP ratios.** Printing
those numbers does not override the exclusion gate. The linear null is computed
from single-pulse calibration responses alone. The historical ratios come from
the invalid backend and are retained solely to show how the record changed.

| Level (mV) | Hz | Source mean | Historical ratio | Corrected STP diagnostic | Static diagnostic | Linear null |
|---:|---:|---:|---:|---:|---:|---:|
| 1.44 | 30 | 1.844 | 1.022 | 1.537 | 3.035 | 1.689 |
| 1.44 | 50 | 2.938 | 1.540 | 3.667 | 8.400 | 2.519 |
| 1.76 | 30 | 1.844 | 1.061 | 2.524 | 4.761 | 1.709 |
| 1.76 | 50 | 2.938 | 1.644 | 5.898 | 13.466 | 2.557 |
| 2.08 | 30 | 1.844 | 1.111 | 3.378 | 7.052 | 1.734 |
| 2.08 | 50 | 2.938 | 1.808 | 8.181 | 16.140 | 2.603 |

The linear null spans 1.689–1.734 at 30 Hz (absolute errors 0.110–0.155); 2.519–2.603 at 50 Hz (absolute errors 0.334–0.419); the original conservative bands can therefore admit a generic linear response. Band inclusion alone has little power to validate CA2-specific dynamics. Signed and relative errors, every seed, all six frequencies and alternative baseline measurements remain in the evidence.

## Numerical and measurement sensitivity

For stp, the largest 20/40 RK change is 0.290 in the mean ratio and 0.795 mV in mean peaks, exceeding the fixed 0.05/0.1 mV gates. For static, the largest 20/40 RK change is 0.890 in the mean ratio and 2.002 mV in mean peaks, exceeding the fixed 0.05/0.1 mV gates. Spike-count or eligibility differences also fail the gate. Larger ratios in spiking traces are not interpretable as facilitated EPSPs. The suite establishes corrected conductance behavior; the neuronal assay remains sensitive around spike threshold.

A descriptive post-outcome audit finds 0–5 of 128 cells per run with first peaks below 0.05 mV. This diagnostic threshold changes no score or exclusion. Sparse recruitment leaves some near-zero responses, making individual normalized ratios sensitive to small baseline or integration differences. The frozen all-cell mean convention is preserved for comparability, rather than filtering cells after observing outcomes. The incremental pre-pulse convention is reported separately. All 240 raw neuron and spike monitors were reread; no failures or ineligible runs were removed.

## Source and assay limits

The [public means_cond16 row](https://github.com/Hippocampome-Org/synaptome_db/blob/master/data/renamed/means_cond16.csv)
differs from the archived selected export. Public
[condition 16 metadata](https://github.com/Hippocampome-Org/synaptome_db/blob/master/data/conditions.csv)
identifies rat, male, P56, 32°C and −60 mV; those labels cannot be assigned to the
archived values without deployed revision/transformation provenance. The
export's `CARLsim_default` flag concerns connection-probability fallback, and
does not certify or negate the physiological ancestry of STP parameters.

The [fitting utility's normalization note](https://github.com/k1moradi/SynapseModelingUtility#note)
states biological g is fitted g times U, supporting retention of the first
impulse normalization. It does not resolve which source data produced this
particular export.

[Sun et al. 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC8482869/) matched initial
EPSPs between control and APV conditions by changing stimulation intensity.
The exact absolute Figure 5 CA2 APV initial amplitude remains unknown here.
Figure 4's 1.76 ± 0.32 mV is a transparently unverified cross-figure setup
assumption, not an established APV amplitude range or animal variability.
The authors' exact peak/baseline convention remains unknown. Digitized source
bands are broad approximate mean-compatibility intervals, not recovered animal
confidence/prediction intervals. No author contact was made and no missing
naturalistic timestamps or assay details were invented.

The assay omits dendrites, recurrence, inhibition and NMDA currents, and cannot
establish CA2's function, behavior, naturalistic replay, or CA1/CA2 differences.

## Readiness for hypotheses

Hippocampome remains useful for assembling traceable candidate cell/connection
models and identifying evidence gaps. This repair distinguishes that usefulness
from tested simulator correctness and from biological validity. The corrected
backend is suitable for bounded mechanistic exploration within its independently
tested dynamics, with the reported 1 ms clock and normalization conventions.
The selected exported somatic assay is **not ready as a quantitatively validated
platform for CA2 functional predictions**: it fails subthreshold and neuronal
numerical gates under the declared setups, and its physiological/assay ancestry
is unresolved. New hypotheses can be explored as explicitly conditional model
comparisons for later biological testing, not as validated CA2 conclusions.
A future study should declare source/preparation assumptions and numerical
criteria before choosing a new configuration; this task did not tune trains
to rescue the benchmark.

The separately versioned raw archive, backend and reproduction instructions
are linked in `evidence/archive.json` and [reproduce.md](reproduce.md). Local unit,
source-integrity, historical evidence, native call-trace and corrected evidence
checks are recorded in `evidence/local_checks.json`; exact-head hosted checks
are visible on PR #1. Hosted CI does not execute GPU simulations.
