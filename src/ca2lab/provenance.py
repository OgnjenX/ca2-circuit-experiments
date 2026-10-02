"""Checksums and constrained archive recovery."""
import hashlib
import json
from pathlib import Path
import tarfile


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_file(path, expected, size=None):
    path = Path(path)
    if size is not None and path.stat().st_size != size:
        raise ValueError(f"Size mismatch: {path}")
    if sha256(path) != expected:
        raise ValueError(f"SHA-256 mismatch: {path}")


def verify_frozen(workspace):
    workspace = Path(workspace)
    plan = json.loads((workspace / "frozen-task-protocol.json").read_text())
    for name, digest in plan["files_sha256"].items():
        verify_file(workspace / name, digest)
    return len(plan["files_sha256"])


def extract_tar(archive, destination):
    """Extract into a new directory; refuse links and unexpected file types."""
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    with tarfile.open(archive) as bundle:
        members = bundle.getmembers()
        for member in members:
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"Unsafe archive path: {member.name}")
            if not (member.isdir() or member.isfile()):
                raise ValueError(f"Unsupported archive member: {member.name}")
        destination.mkdir(parents=True)
        bundle.extractall(destination, members=members, filter="data")
