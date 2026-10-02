# Adding an experiment

Copy `experiments/template/` to the next numbered directory. Choose a short name
that describes the question, such as `002_ca2_slice_validation`.

Before running, record the biological target, source data, modeled inputs,
measured outputs, controls, numerical checks and criteria for accepting or
rejecting agreement. State which observations are calibration targets and which
are held out for validation. Missing measurements remain missing.

Commit the plan and model configuration before inspecting test outcomes. Every
run records that commit, input checksums, simulator version, parameters and random
seeds. Changes after inspection require a new protocol revision; the earlier run
and its results remain available.

Use paired inputs and network seeds for interventions. A classifier uses only its
declared training data. Network seeds are model replicates, not animals. Keep null
outcomes, failed runs, excluded attempts and numerical failures in the report.

Keep reusable mechanics in `src/ca2lab/` and simulator or circuit changes in their
own directories. Keep the scientific choices in the experiment. Reusing software
does not transfer biological validation from one experiment to another.

At completion, save a result summary, figures, exact configuration, raw-data
checksums and instructions for reproducing the analysis. Publish a versioned
release when the record is ready to share.
