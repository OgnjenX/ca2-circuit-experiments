"""Recover the original experiment records without rewriting their paths."""
import argparse
from pathlib import Path
import subprocess
import tempfile
from _common import checked_asset
from ca2lab.provenance import extract_tar

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("destination", type=Path)
args = parser.parse_args()
if args.destination.exists():
    raise FileExistsError(args.destination)
archive = checked_asset("recorded")
with tempfile.TemporaryDirectory() as temporary:
    uncompressed = Path(temporary) / "recorded.tar"
    with uncompressed.open("wb") as target:
        subprocess.run(["zstd", "-d", "-c", str(archive)], stdout=target, check=True)
    extract_tar(uncompressed, args.destination)
print(args.destination.resolve())
