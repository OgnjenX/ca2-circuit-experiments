# Model provenance

The parameter source is the Hippocampome simulation export captured on
2026-10-01. The selected tables contain 14 neuron types and 87 connection rows.
The implemented circuit uses 51 connection rows, including 25 marked as defaults.
An unflagged row does not imply that every field was measured directly.

The core includes 18,956 CA2 pyramidal cells, 105 basket cells, 147 wide-arbor
basket cells, 79 bistratified cells and 94 SP-SR cells. Inputs are prescribed MEC
layer-II and CA3 spikes. CA1 is a feedforward assay of 128 pyramidal targets and
selected inhibitory populations. Feedback, explicit dendrites and long-term
learning are absent. MEC layer II is not a substitute for LEC social input.

The nominal experiment uses an assumed global GABAa reversal of -77.8 mV and a
fitted multiplier of 100 on four inhibitory-to-CA2-pyramidal connections. These
are experiment-specific assumptions and calibration, not measured synaptic
strengths. AMPA/GABAa and exported pair-specific short-term plasticity are active;
the packaged driver's NMDA/GABAb multipliers are zero.

Calibration used published single-pulse physiology. Separate train responses,
precision checks and a downstream adequacy check are retained. The CA1 check was
not matched to the slice holding conditions and produced spikes, so it could not
validate the intended subthreshold EPSP comparison.

The backend is CARLsim4, upstream commit
`11ea96f750d125e4dcfbf67231429204322fa1bd`, from the Hippocampome branch.
Local changes provide CUDA 12 compatibility, sm_86 targeting, a 128-cell monitor
cap and a configurable inhibitory reversal in both numerical backends. The
study used GPU mode. Archived CPU return-type warnings remain unresolved and
CPU simulation is not validated.

Sources:

- [Hippocampome parameter selector](https://hippocampome.org/php/simulation_parameters.php)
- [Chevaleyre and Siegelbaum (2010)](https://pmc.ncbi.nlm.nih.gov/articles/PMC2905041/)
- [CARLsim4 source](https://github.com/UCI-CARL/CARLsim4/tree/11ea96f750d125e4dcfbf67231429204322fa1bd)

Exact tables, source hashes, build logs and calibration results are linked from
experiment 001. No behavioral recording was supplied as the task input.
