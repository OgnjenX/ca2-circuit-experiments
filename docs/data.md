# Data and archives

The parameter exports and compact reference results are tracked in Git. Raw
monitor files, executables, installed libraries and complete historical records
are release assets. Downloads are checked with SHA-256 before extraction.

`artifacts/experiment_001.json` records asset filenames, sizes and checksums.
If the recorded archive is split into parts, the recovery tool verifies each
part, joins them in the declared order and verifies the combined archive.

The runtime bundle is a fresh-run input, with frozen executable and stimulus
files plus two explicitly retained seed-20 reference fixtures. It contains no
completed nominal, sensitivity or generalization task runs. The recorded bundle
contains the actual historical runs and their failed and excluded attempts.

These are synthetic simulation records, not recordings of an animal's behavior.
The Git history tracks changes to source and interpretation; archive checksums
identify the underlying data.

The recorded archive stores the three library symlinks as their target file
bytes, so recovery does not need to create links. The original file-content
checksums remain valid. Recovery requires the `zstd` command and about 22 GB
of free space while the tar stream and extracted records coexist.
