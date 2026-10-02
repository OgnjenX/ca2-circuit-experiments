# Pre-run outcome: source and model-semantic gates blocked

No production experiment or biological agreement inspection has occurred.
This is a preserved blocked preregistration, not a completed firing benchmark.
Nine control means are readable in the accessible official asset. The 100 pA
blue marker is fully covered by the red marker, so its mean remains missing.
No separate SEM endpoints can be read; hidden and absent bars cannot be
 distinguished. Missing values have not been replaced with zero.

## What is established

The isolated checkout starts at normal merge
`ffb10ccb60b36742b9906b3c3001bb31ff46b105` and retains full historical ancestry.
The model CSV was read directly. Its unrounded CA2 vector is C=1630,
k=5.9432435, Vr=-72.58829, Vt=-58.78362, a=0.0011350543,
b=-15.885261, Vpeak=19.99006, Vmin=-62.646779, d=74. Holding at -70 mV
gives u=-41.11566219369 pA and I=+131.42409113662896 pA. An independent
Decimal calculation agrees. The rounded vector supplied in the delegation gives
different holding values; it does not replace archived parameters.

The [article](https://pmc.ncbi.nlm.nih.gov/articles/PMC9547935/) RESULTS and
figure caption identify blue controls, one-second 100–1000 pA steps, and
92 cells from 48 control mice. Controls are NON-PILO animals that received
methylatropine, diazepam and levetiracetam, not untreated animals. Other detailed
preparation conditions are recorded from the delegation; subsequent methods
access was blocked by CAPTCHA and still needs independent verification.
The [Zenodo record](https://zenodo.org/records/6835900) contains analysis code,
not raw recordings. Its MLX document was inspected: baseline subtraction,
20 kHz sampling, 60 mV peak-height threshold and 6 ms separation operate on the
imported trace. Localized model events would require the adapter and whole-trace
versus pulse-window audit specified in the protocol. Ramp assays are excluded.

## Source extraction and reconciliation

Two independent model-blind passes preserve original pixel coordinates,
calibrations and conservative reading intervals. No simulated response existed
during extraction. Reconciliation uses the average of the two readings and the
union of their uncertainty intervals. The partially occluded 200 pA reading is
constrained to physical nonnegative firing; its signed raw axis reading is
retained in pass A. The 100 pA target has no supported center or interval.
The accessible official JPG is 1447×1561; highest possible publisher resolution
has not been established. Attempts and access failures are recorded. Enlarging
this image cannot restore hidden points.

| Step (pA) | Reconciled mean (Hz) | Reading interval (Hz) | Paper SEM | Model / residual |
|---:|---:|---:|---|---|
| 100 | missing | missing | missing | not run |
| 200 | 0.000 | 0.000–0.284 | missing | not run |
| 300 | 0.260 | 0.047–0.521 | missing | not run |
| 400 | 1.823 | 1.596–2.045 | missing | not run |
| 500 | 4.469 | 4.225–4.699 | missing | not run |
| 600 | 7.497 | 7.230–7.738 | missing | not run |
| 700 | 10.280 | 10.000–10.524 | missing | not run |
| 800 | 12.931 | 12.629–13.187 | missing | not run |
| 900 | 15.147 | 14.836–15.414 | missing | not run |
| 1000 | 16.802 | 16.479–17.079 | missing | not run |

These intervals are digitization bounds, not confidence intervals or SEM.
Ten-point signed mean error, RMSE, maximum absolute error and their bounds are
unavailable. A nine-point substitute or imputed tenth point would change the
requested scoring and has not been used.

## Unexpected executable-model difference

The archived CSV includes `Refractory Period=1`, and the existing harness passes
it to CARLsim. Inspection of the corrected CPU RK4 9-parameter branch shows a
counter-based refractory interval that suppresses both voltage and recovery
updates and clamps V to Vmin at the last substep. Threshold detection examines
the previous nextVoltage state before integration. The specified high-accuracy
hybrid reference instead localizes an upward Vpeak crossing, resets immediately,
and resumes both ODEs immediately. Dropping the clamp would change executable
model behavior, not just improve integration accuracy. Independent review
confirmed this discrepancy and the target occlusion. No backend was altered.

Both independent DOP853 reference candidates remain unexecuted. The immediate
reset candidate does not validate the archived CARLsim refractory model.
The user reviewed the choice and selected existing CARLsim semantics as primary,
with standard immediate reset as a separate diagnostic. Both choices are recorded
before biological comparison. Production implementation and numerical verification
remain incomplete while the source gate is blocked.

## Remaining work after review

A complete honest ten-point source, confirmation of highest official resolution,
and independent verification of detailed recording methods must precede a new
committed preregistration. The primary reset/refractory choice is now authorized.
Then implement and independently review production integration, refine it and
reference tolerances separately, verify spike counts, event order, reset states
and 0.05 ms event timing, retain failures, and only then score biological
residuals. Holding-only, same-equilibrium sweeps, fixed pre/post windows,
6 ms detector exclusion and pulse-end ambiguity are already specified.

No biological equivalence margin is supplied. Even a numerically verified
comparison would quantify discrepancy for this somatic point model, with
population-level validation limited by repeated currents, cells nested in mice,
unknown covariance and request-only voltages. It would not validate synapses,
networks or Hippocampome generally. No temperature compensation, model tuning,
current-axis fitting, artificial cell variance, release changes or prior
experiment edits occurred.
