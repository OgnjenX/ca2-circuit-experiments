"""Restore a checked runtime bundle into a new, separate workspace."""
import argparse
from pathlib import Path
import tempfile
import shutil
from _common import checked_asset
from ca2lab.provenance import extract_tar, verify_frozen

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("destination", type=Path)
args = parser.parse_args()
destination = args.destination.resolve()
if destination.exists():
    raise FileExistsError(destination)
archive = checked_asset("runtime")
with tempfile.TemporaryDirectory() as temporary:
    extracted = Path(temporary) / "extract"
    extract_tar(archive, extracted)
    workspace = extracted / "workspace"
    count = verify_frozen(workspace)
    if (workspace / "reset-task-execution-complete.json").exists() or (workspace / "runs/reset-task-v1").exists():
        raise ValueError("Runtime bundle contains task outcomes")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(workspace, destination)
print(f"Prepared {destination}; verified {count} frozen artifacts")
