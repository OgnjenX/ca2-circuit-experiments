# Repository layout

| Path | Contents |
| --- | --- |
| `src/ca2lab/` | Shared monitor readers, event checks, decoding and checksum utilities. |
| `models/ca2_carlsim/` | Native circuit code and configurations used in experiment 001. |
| `simulators/carlsim4/` | Upstream source identity, local patch and build instructions. |
| `data/hippocampome/2026-10-01/` | Exact exported parameter tables. |
| `experiments/001_input_patterns/` | The existing study: protocol, unchanged implementation, reference results and plots. |
| `experiments/template/` | Starting point for a new numbered study. |
| `artifacts/` | Release asset names, locations and checksums. |
| `scripts/` | Repository checks, data recovery and reproduction entrypoints. |
| `tests/` | Small tests of shared code and malformed-record handling. |

`data/downloads/`, `data/workspaces/` and `data/recorded/` are ignored. They hold
downloaded assets, fresh runs and extracted historical records respectively.
Generated outputs belong in a workspace, not beside shared code.

The experiment implementation is a historical snapshot. Its scripts expect a
flat working directory, so the runtime bundle restores that layout in a new
workspace. Source paths are mapped in `experiments/001_input_patterns/provenance/source_map.json`.
New experiments can use `ca2lab` directly and keep their own plans and outputs.
