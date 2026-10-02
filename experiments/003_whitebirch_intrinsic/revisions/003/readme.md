# Output serialization recovery

The original numerical controller completed 33 native traces and 66 independent clock-reference integrations, then failed while serializing a NumPy boolean in an aggregate gate. It did not write the numerical aggregate, run the immediate-reset diagnostic, or inspect biological agreement. `original_failure.json` preserves this failure.

This separate amendment reads all pinned existing raw files and invokes the unchanged revision 002 validation functions and numerical criteria. NumPy scalars become Python scalars only at the JSON write boundary. It does not rerun the clock integrations, edit the frozen model/backend/target or change a failed numerical gate. It then invokes the originally preregistered, unchanged immediate-reset diagnostic.

After the reviewed recovery manifest is committed:

```sh
.venv-whitebirch/bin/python experiments/003_whitebirch_intrinsic/revisions/003/recover.py --workspace data/workspaces/003-whitebirch-gpu-pre-freeze-v7 --references data/workspaces/003-whitebirch-numerics-v1 --output data/workspaces/003-whitebirch-numerics-v2 --recovery-commit <recovery-freeze-commit>
```

An exit status of 1 means a numerical gate failed; retain the written evidence and do not score biological disagreement. The original scientific freeze remains `233b068cb7e22663b9ce551806e4a4e573a63872`. The recovery commit is recorded separately. Any later tighter source-only reading of the hidden 100 pA marker is a sensitivity analysis and must not replace the frozen target.
