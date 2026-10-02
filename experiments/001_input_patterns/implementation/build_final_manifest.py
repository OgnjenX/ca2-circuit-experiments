"""Hash the completed experiment, including raw outputs, without claiming scientific validity."""
from pathlib import Path
import hashlib
import json
import time

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / 'artifact-manifest.json'
EXCLUDED_PARTS = {'__pycache__', 'plot-deps', '.git'}
REQUIRED = [
    'nominal-experiment-audit.json', 'extended-experiment-audit.json',
    'generalization-results.json', 'sensitivity-results.json',
    'variant-precision-results.json', 'reproduction-copy-validation.json',
    'output/pdf/ca2-scientific-experiment.pdf',
]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    for name in REQUIRED:
        assert (ROOT / name).is_file(), f'Missing final artifact: {name}'
    nominal = json.loads((ROOT / REQUIRED[0]).read_text())
    extended = json.loads((ROOT / REQUIRED[1]).read_text())
    assert nominal['all80trials_complete'] and nominal['verified_readout_runs'] == 240
    assert extended['complete']
    state = json.loads((ROOT / 'followon-pipeline-state.json').read_text())
    assert state['phase'] == 'analyses and figures complete; scientific review and report verification remain'
    entries = {}
    for path in sorted(ROOT.rglob('*')):
        relative = path.relative_to(ROOT)
        if not path.is_file() or path == TARGET or relative.as_posix() == 'completion-audit.json' or EXCLUDED_PARTS.intersection(relative.parts):
            continue
        # Rendered preview files are redundant with the PDF and separately reviewed.
        if relative.parts[:2] == ('tmp', 'pdfs'):
            continue
        before = path.stat()
        checksum = digest(path)
        after = path.stat()
        assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), f'Changed while hashing: {relative}'
        entries[str(relative)] = {'sha256': checksum, 'bytes': after.st_size}
    document = {
        'status': 'Final artifact inventory; integrity evidence, not a claim that the model is biologically validated.',
        'generated_unix': time.time(),
        'root': str(ROOT),
        'required_artifacts': REQUIRED,
        'excluded': ['artifact-manifest.json itself', 'completion-audit.json (verifies this inventory; excluded to avoid a circular hash)', '__pycache__', 'plot-deps', '.git', 'tmp/pdfs rendered previews'],
        'files': entries,
        'file_count': len(entries),
        'total_bytes': sum(e['bytes'] for e in entries.values()),
    }
    TARGET.write_text(json.dumps(document, indent=2) + '\n')
    print(f'Hashed {document["file_count"]} files ({document["total_bytes"]:,} bytes).')


if __name__ == '__main__':
    main()
