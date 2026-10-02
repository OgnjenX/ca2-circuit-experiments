"""Rebuild the patched backend and nominal circuit in a new directory."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
from _common import ROOT, checked_asset
from ca2lab.provenance import verify_file, sha256

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("destination", type=Path)
parser.add_argument("--prepare-only", action="store_true")
parser.add_argument("--compiler", default="g++-12")
parser.add_argument("--nvcc", default="nvcc")
parser.add_argument("--jobs", type=int, default=2)
parser.add_argument("--reversal", type=float, choices=[75.0, 77.8, 80.0], default=77.8)
args = parser.parse_args()
if args.jobs < 1:
    parser.error("--jobs must be positive")
destination = args.destination.resolve()
if destination.exists():
    raise FileExistsError(destination)
archive = checked_asset("source")
source_identity = json.loads((ROOT / "simulators/carlsim4/source.json").read_text())
verify_file(archive, source_identity["archive_sha256"])
destination.mkdir(parents=True)
source = destination / "backend"
source.mkdir()
with zipfile.ZipFile(archive) as bundle:
    names = bundle.namelist()
    prefix = names[0].split("/")[0]
    for item in bundle.infolist():
        path = Path(item.filename)
        if path.is_absolute() or ".." in path.parts or path.parts[0] != prefix:
            raise ValueError("Unsafe ZIP path")
        if item.is_dir():
            continue
        if (item.external_attr >> 16) & 0o170000 == 0o120000:
            raise ValueError("Unexpected ZIP symlink")
        target = source.joinpath(*path.parts[1:])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(bundle.read(item))
patch = ROOT / "simulators/carlsim4/patches/experiment_001.patch"
with patch.open("rb") as stream, (destination / "patch.log").open("w") as log:
    subprocess.run(["patch", "--batch", "--fuzz=0", "-p1"], stdin=stream, stdout=log,
                   stderr=subprocess.STDOUT, cwd=source, check=True)
expected = source_identity["recorded_builds"][0]["source_and_build_file_sha256"]
for name, digest in expected.items():
    verify_file(source / name, digest)
record = {"upstream_commit": source_identity["commit"], "source_archive_sha256": sha256(archive),
          "patch_sha256": sha256(patch), "verified_source_files": len(expected),
          "architecture": "sm_86 plus compute_86 PTX", "GABAa_reversal_mV": -args.reversal,
          "numerical_status": "New build; requires renewed numerical validation"}
if not args.prepare_only:
    nvcc = shutil.which(args.nvcc)
    if not nvcc or not shutil.which(args.compiler):
        raise FileNotFoundError("CUDA compiler or host compiler unavailable")
    command = ["make", f"-j{args.jobs}", f"CXX={args.compiler}",
               f"NVCC={nvcc} -ccbin {args.compiler}", "CUDA_PATH=",
               f"CA2_GABAA_MAGNITUDE={args.reversal}f"]
    record["backend_command"] = command
    with (destination / "build.log").open("w") as log:
        subprocess.run(command, cwd=source, stdout=log, stderr=subprocess.STDOUT, check=True)
    library = source / "libcarlsim.a.4.0.0"
    record["library_sha256"] = sha256(library)
    # nvcc classifies positional inputs by suffix; make emits only the versioned file.
    link_library = destination / "carlsim_rebuilt.a"
    shutil.copy2(library, link_library)
    model = destination / "model"
    shutil.copytree(ROOT / "models/ca2_carlsim/nominal", model)
    header_directories = sorted({p.parent for directory in (source / "carlsim", source / "tools")
                                 for p in directory.rglob("*.h")})
    command = [nvcc, "-ccbin", args.compiler, "-m64", "-gencode", "arch=compute_86,code=sm_86",
               "-gencode", "arch=compute_86,code=compute_86",
               *[f"-I{p}" for p in header_directories], str(model / "src/circuit.cpp"),
               str(link_library), "-lcurand", "-lcudart", "-lpthread", "-o", str(model / "circuit-rebuilt")]
    record["circuit_command"] = command
    with (destination / "circuit-build.log").open("w") as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    record["executable_sha256"] = sha256(model / "circuit-rebuilt")
(destination / "rebuild.json").write_text(json.dumps(record, indent=2))
print(json.dumps(record, indent=2))
