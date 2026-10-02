"""Verify canonical relocation plus both immutable assay revisions."""
from pathlib import Path
import subprocess, sys
ROOT=Path(__file__).resolve().parents[2]
subprocess.run([sys.executable,str(ROOT/'scripts/verify_assay_revisions.py')],check=True)
