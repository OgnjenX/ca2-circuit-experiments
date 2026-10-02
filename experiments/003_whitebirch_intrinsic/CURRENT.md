# Experiment 003 current record

The [executed result](results/report.md) is a failed primary numerical verification with biological scoring gated. The separate immediate-reset diagnostic passed its numerical refinements.

The root report/readme preserve the first blocked preregistration. [Revision 002](revisions/002/readme.md) is the runnable scientific freeze; [revision 003](revisions/003/readme.md) records the separately reviewed serialization-only recovery. Previous experiments, backend files and historical releases/tags remain unchanged.

Two separately authorized post-hoc addenda preserve that result:

- [Exploratory biological comparison](addenda/posthoc_biological_comparison/report.md): all ten existing GPU pulse counts exceed the frozen reading intervals; conditional RMSE 6.8434–7.2053 spikes/s. This does not reopen gated primary scoring or establish biological validation.
- [Bounded pre-reset diagnostic](addenda/004_prefix_diagnostic/report.md): at 100 pA/80 substeps, float64 RK4 matches DOP853, while explicit float32 operations closely follow the GPU drift. This supports accumulated operation rounding in this condition; original event/reset gates remain failed.

The prefix design was frozen at `bff3d5ffd1e08ac46dbea3b95e9cade94f9f99bc` before new diagnostic integrations. [Independent result audit](addenda/004_prefix_diagnostic/result_review.json), raw archive metadata and compact checks accompany the report. No new conditions, model/backend changes or merges were performed.
