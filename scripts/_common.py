from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ca2lab.provenance import verify_file


def index():
    return json.loads((ROOT / "artifacts/experiment_001.json").read_text())


def checked_asset(kind):
    asset = index()["assets"][kind]
    path = ROOT / "data/downloads" / asset["filename"]
    verify_file(path, asset["sha256"], asset["bytes"])
    return path.resolve()
