# Whitebirch intrinsic firing benchmark: blocked pre-run record

Experiment 003 targets the blue NON-PILO control series in Whitebirch et al.
2022 Figure 1C. No production simulation or biological comparison has run.
The complete-target source gate failed before production. The reset/refractory
choice was reviewed and resolved before simulation. See
[report.md](report.md), [protocol.json](protocol.json), and
[target_data.json](target_data.json).

The exact archived intrinsic vector remains unchanged. Both independent reference
implementations are preparatory and unexecuted. The user selected existing CARLsim
reset/refractory semantics as primary, with standard immediate reset as a separate
diagnostic. A complete honest target is necessary before committing a new
preregistration revision and starting production.

From repository root, validate this frozen blocked record:

```sh
python experiments/003_whitebirch_intrinsic/verify_readiness.py
python experiments/003_whitebirch_intrinsic/verify_readiness.py --require-ready
```

The first command checks integrity and reports gates. The second exits 2 because
production is blocked; a successful integrity check is not scientific readiness.
There is no approved production run command. The candidate reference needs NumPy
and SciPy; syntax checks deliberately do not import or execute it.

The retained 1 MB official figure is source evidence, not raw recording data.
Its URL/checksum and author analysis-code checksum are in
[source/source_audit.json](source/source_audit.json). No new release or tag was
created. Any future archive should use `experiment-003-whitebirch-v1` or another
unambiguous new identifier, never the historical `experiment-003-v1`.
