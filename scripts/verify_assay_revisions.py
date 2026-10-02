"""Check relocated corrected bytes and verify both original frozen Git snapshots."""
import argparse
import hashlib
import json
import subprocess
import sys
from assay_snapshot import ROOT, SNAPSHOT, PATHS, snapshot


def verify_relocation():
    here = ROOT / PATHS['original']
    mapping = json.loads((here / 'provenance_map.json').read_text())
    if mapping['frozen_snapshot_commit'] != SNAPSHOT or mapping['corrected_path'] != PATHS['corrected']:
        raise ValueError('Unexpected assay snapshot identity')
    expected = mapping['relocated_files_sha256']
    names = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only',
                                     SNAPSHOT, PATHS['corrected']], text=True).splitlines()
    prefix = PATHS['corrected'] + '/'
    if set(expected) != {name[len(prefix):] for name in names}:
        raise ValueError('Incomplete relocation map')
    adapters = {'readme.md', 'reproduce.md', 'verify_evidence.py'}
    if set(mapping['navigation_and_adapter_files']) != adapters:
        raise ValueError('Unexpected relocation exceptions')
    for name, digest in expected.items():
        original = subprocess.check_output(['git', '-C', str(ROOT), 'show',
                                           f'{SNAPSHOT}:{prefix}{name}'])
        if hashlib.sha256(original).hexdigest() != digest:
            raise ValueError('Snapshot hash mismatch: ' + name)
        if name not in adapters and hashlib.sha256((here / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Relocated frozen file changed: ' + name)
    frozen = json.loads((here / 'frozen_configuration.json').read_text())
    for name, digest in frozen['scientific_file_sha256'].items():
        relocated = (PATHS['original'] + name[len(PATHS['corrected']):]
                     if name.startswith(PATHS['corrected'] + '/') else name)
        if hashlib.sha256((ROOT / relocated).read_bytes()).hexdigest() != digest:
            raise ValueError('Current scientific source changed: ' + relocated)
    if (ROOT / PATHS['corrected']).exists():
        raise ValueError('Obsolete active experiment 003 directory remains')
    print(f'Verified {len(expected)} corrected file mappings to canonical experiment 002.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', choices=['both', 'original', 'corrected'], default='both')
    args = parser.parse_args()
    verify_relocation()
    with snapshot() as tree:
        revisions = PATHS if args.revision == 'both' else [args.revision]
        for revision in revisions:
            subprocess.run([sys.executable, str(tree / PATHS[revision] / 'verify_evidence.py')],
                           cwd=tree, check=True)
    print('Historical manifests and scores were verified at their original paths; no simulations ran.')

if __name__ == '__main__':
    main()
