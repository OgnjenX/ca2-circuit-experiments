"""Download verified release assets. Existing correct files are reused."""
import argparse
from pathlib import Path
import shutil
import urllib.request
from _common import ROOT, index, checked_asset
from ca2lab.provenance import verify_file

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("kind", choices=["runtime", "recorded", "source"])
args = parser.parse_args()
asset = index()["assets"][args.kind]
destination = ROOT / "data/downloads"
destination.mkdir(parents=True, exist_ok=True)
parts = asset.get("parts", [asset])
for part in parts:
    path = destination / part["filename"]
    if path.exists():
        verify_file(path, part["sha256"], part["bytes"])
        continue
    partial = path.with_name(path.name + ".partial")
    print(f"Downloading {part['filename']}", flush=True)
    with urllib.request.urlopen(part["url"]) as source, partial.open("wb") as target:
        shutil.copyfileobj(source, target)
    verify_file(partial, part["sha256"], part["bytes"])
    partial.replace(path)
if "parts" in asset and not (destination / asset["filename"]).exists():
    partial = destination / (asset["filename"] + ".partial")
    with partial.open("wb") as target:
        for part in parts:
            with (destination / part["filename"]).open("rb") as source:
                shutil.copyfileobj(source, target)
    verify_file(partial, asset["sha256"], asset["bytes"])
    partial.replace(destination / asset["filename"])
print(checked_asset(args.kind))
