# Protocol

The exact frozen definition is `reference/frozen-task-protocol.json`.

Two cortical patterns each activate 9,800 of 10,818 source cells; 8,820 are shared.
Each active cell receives five events at 100 Hz with 0–2 ms jitter. CA3 input,
when present, activates 1,940 of a 4,096-cell pool, starting 25 ms after cortex.
Trials last 250 ms and start a fresh simulator process.

Five independent network seeds, 31–35, each have 16 trials: two identities,
two CA3 contexts and four repetitions. The first two repetitions train the
readout; the last two are held out. Calibration seed 20 is excluded.

Each core response supplies three matched CA1 replays: intact pyramidal output,
blocked pyramidal output and a bijective permutation of pyramidal cell identities.
The four inhibitory streams and direct CA3 stream stay unchanged. Scrambling
preserves spike times and counts. Blocking is not a whole-CA2 lesion.

The primary feature is per-cell spike count in four 50 ms windows. A nearest
centroid classifier is trained separately for each network, context and output
condition; equal distances score 0.5. The secondary feature is window-mean voltage
after subtracting the 40–49 ms baseline. No classifier tuning replaces the primary
result. Five network seeds support descriptive uncertainty, not animal inference.

The sensitivity plans precede their outcomes: inhibitory reversal -75/-80 mV,
fitted inhibition 50/150, default-flagged output strength half/double and higher
integration precision. Core parameter screens use seed 31; output screens use
all five. Numerical failures remain recorded.

Unseen tests replace 10% or 50% of distinctive input cells and change CA3 delay
to 15 or 35 ms. Their centroids remain fixed to nominal training trials; new
test responses never train the readout. New jitter limits exact timing attribution.
