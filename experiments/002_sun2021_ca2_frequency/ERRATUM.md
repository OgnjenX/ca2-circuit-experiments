# Historical backend defect and revision numbering

The original experiment 002 used the defective receptor dynamics and its
biological interpretation is invalid. Experiment 001 shares that backend and
requires revalidation. Silent afferents changed active receptor decay; static
and mixed-STP event/configuration paths also had defects. The corrected backend
uses independent per-synapse receptor states and preserves first-impulse
normalization. Its independent oracle passes, but all corrected assay setups
fail the numerical/coverage eligibility requirements. See [report.md](report.md).

The corrected run was provisionally numbered 003. It now lives here as the
corrected revision of experiment 002. Its frozen identifiers and published
`experiment-003-v1` release deliberately retain their original names.
Experiment 003 is free for a new scientific question. This relocation changes
no biology, code used to generate the results, calibration, scoring or values.

The exact pre-consolidation snapshot is
[81cbbb7ad130c4575713b99dba96b2743ecb5650](https://github.com/OgnjenX/ca2-circuit-experiments/tree/81cbbb7ad130c4575713b99dba96b2743ecb5650).
Its [original revision](https://github.com/OgnjenX/ca2-circuit-experiments/tree/81cbbb7ad130c4575713b99dba96b2743ecb5650/experiments/002_sun2021_ca2_frequency)
and [corrected revision](https://github.com/OgnjenX/ca2-circuit-experiments/tree/81cbbb7ad130c4575713b99dba96b2743ecb5650/experiments/003_corrected_ca2_frequency)
preserve every tracked historical byte. Large raw files remain in the unchanged
[original release](https://github.com/OgnjenX/ca2-circuit-experiments/releases/tag/experiment-002-v1)
and [corrected release](https://github.com/OgnjenX/ca2-circuit-experiments/releases/tag/experiment-003-v1),
including the supplemental diagnostic asset. Git alone does not store those raw
archives.

`python scripts/verify_assay_revisions.py` reconstructs both snapshots temporarily
at their original paths and runs their unchanged integrity/scoring verifiers.
It also checks every relocated frozen file against its pinned Git blob. No
historical archive directory is carried in the current tree.
