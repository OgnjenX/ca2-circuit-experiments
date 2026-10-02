"""Restore immutable assay paths locally without keeping duplicate working trees."""
from contextlib import contextmanager
import io
from pathlib import Path
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = '81cbbb7ad130c4575713b99dba96b2743ecb5650'
PATHS = {'original': 'experiments/002_sun2021_ca2_frequency',
         'corrected': 'experiments/003_corrected_ca2_frequency'}

@contextmanager
def snapshot():
    # git archive reads only the pinned, tracked tree; no downloads or raw runs.
    archive = subprocess.check_output(['git', '-C', str(ROOT), 'archive', SNAPSHOT])
    with tempfile.TemporaryDirectory(prefix='ca2-assay-snapshot-') as directory:
        tree = Path(directory)
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            source.extractall(tree, filter='data')
        yield tree
