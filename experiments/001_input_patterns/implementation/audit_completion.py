"""Requirement-level completion review. Biological failures remain failures."""
from pathlib import Path
import ast
import datetime
import hashlib
import json
import subprocess
import numpy as np

ROOT = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(name):
    return json.loads((ROOT / name).read_text())


def main():
    inventory = read('artifact-manifest.json')
    for name, item in inventory['files'].items():
        path = ROOT / name
        assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], name
    assert inventory['file_count'] == len(inventory['files'])
    protocol = read('frozen-task-protocol.json')
    for name, expected in protocol['files_sha256'].items():
        assert sha(ROOT / name) == expected, name
    assert len(protocol['files_sha256']) == 14

    source = read('circuit-source-audit.json')
    for name, expected in source['files'].items():
        assert sha(ROOT / 'revised-source-export' / Path(name).name) == expected
    parameters = read('nominal-parameter-classification.json')
    assert (source['neuron_rows'], source['connection_rows']) == (14, 87)
    assert (parameters['count_rows'], parameters['default_flagged_rows']) == (51, 25)
    assert read('export-consistency-audit.json')['pass']

    backend = read('backend-source-provenance.json')
    assert backend['complete'] and backend['embedded_archive_commit'] == '11ea96f750d125e4dcfbf67231429204322fa1bd'
    archive = ROOT.parent / 'ca2-simulation/rebuild/source.zip'
    assert sha(archive) == backend['archive_sha256']
    for variant in backend['variants']:
        directory = ROOT / variant['directory']
        assert sha(directory / 'libcarlsim.a.4.0.0') == variant['library_sha256']
        for name, expected in variant['source_and_build_file_sha256'].items():
            assert sha(directory / name) == expected
    runtime_log = ROOT / 'runs/reset-task-v1/seed31-ctx0-id0-rep0/core/results/carlsim.log'
    assert backend['execution_evidence']['runtime_partition_message'] in runtime_log.read_text()

    nominal = read('nominal-experiment-audit.json')
    extended = read('extended-experiment-audit.json')
    assert nominal['all80trials_complete'] and (nominal['verified_trials'], nominal['verified_readout_runs']) == (80, 240)
    assert nominal['pending_trials'] == []
    assert nominal['trials_verified_by_network'] == {str(k): 16 for k in range(31, 36)}
    assert extended['complete'] and (extended['total_verified_core_runs'], extended['total_verified_readouts']) == (208, 1344)
    assert len(extended['variants']) == 13

    primary = read('reset-task-results.json')
    secondary = read('secondary-voltage-results.json')
    assert len(primary['trials']) == 240 and len(primary['per_seed_context_condition']) == 30
    assert all(row['heldout_accuracy'] == .5 for row in primary['per_seed_context_condition'])
    assert len(secondary['per_seed_context_condition']) == 30
    assert set(primary['permutation_null']) == {'intact', 'blocked', 'scrambled'}
    assert all(row['permutations'] == 1000 for row in primary['permutation_null'].values())
    assert len(primary['paired_effects']) == len(secondary['paired_effects']) == 2

    # Independently check the nominal stimulus control with the frozen decoder.
    ns = {'np': np}
    tree = ast.parse((ROOT / 'analyze_reset_task_v2.py').read_text())
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    exec(compile(ast.Module(body=functions, type_ignores=[]), 'frozen-analysis-functions', 'exec'), ns)
    controls = []
    for seed in range(31, 36):
        for context in (0, 1):
            trials = [t for t in protocol['stimulus_definition']['trials'] if t['network_seed'] == seed and t['context'] == context]
            counts = []
            for trial in trials:
                events = np.loadtxt(ROOT / 'stimuli/reset-task-v1' / trial['name'] / 'MEC_LII_Stellate.txt', dtype=np.int32)
                counts.append(np.bincount(events[:, 1], minlength=10818))
            x = np.stack(counts); y = np.array([t['identity'] for t in trials])
            train = np.array([t['split'] == 'train' for t in trials]); test = ~train
            identity = ns['decoder'](x, y, train, test)
            total = ns['decoder'](x.sum(1, keepdims=True), y, train, test)
            assert identity == 1 and total == .5
            controls.append({'seed': seed, 'context': context, 'input_identity_accuracy': identity, 'total_count_accuracy': total})

    generalization = read('generalization-results.json')
    assert (len(generalization['rows']), len(generalization['paired_effects']), len(generalization['core_response_rows'])) == (90, 24, 600)
    assert all(row['spikes'] == .5 for row in generalization['rows'])
    assert len(generalization['input_positive_controls']) == 30
    assert all(row['fixed_input_decoder_accuracy'] == 1 and row['total_count_accuracy'] == .5 for row in generalization['input_positive_controls'])
    assert read('sensitivity-unit-gain-validation.json')['pass']
    assert len(read('sensitivity-results.json')['variants']) == 9
    assert read('readout-precision40vs80-results.json')['pass']
    precision = read('variant-precision-results.json')
    assert precision['complete'] and len(precision['results']) == 8
    failed = [row for row in precision['results'] if not row['pass']]
    assert len(failed) == 1 and failed[0]['variant'] == 'egaba77p8-gain150'
    assert not read('ca1-adequacy-results.json')['reference_comparison_eligible']

    reproduction = read('reproduction-copy-validation.json')
    assert reproduction['complete'] and reproduction['frozen_hashes_checked'] == 14
    assert reproduction['nominal_input_files_checked'] == 160 and reproduction['new_input_audit']['trials'] == 120
    for name in ('REPRODUCE.txt', 'methods.txt', 'prepare_reproduction_copy.py'):
        assert (ROOT / name).is_file() and sha(ROOT / name) == inventory['files'][name]['sha256']
    for name in ('generalization-scientific-review.json', 'sensitivity-scientific-review.json'):
        for source_name, expected in read(name)['evidence_sha256'].items():
            assert sha(ROOT / source_name) == expected

    visual = read('report-visual-review.json'); pdf = ROOT / 'output/pdf/ca2-scientific-experiment.pdf'
    assert visual['page_count'] == 7 and sha(pdf) == visual['pdf_sha256']
    text = ' '.join(subprocess.check_output(['pdftotext', str(pdf), '-'], text=True).split())
    for phrase in ('39 to 36', '1,584', '7 of 8', '95%', 'biological', 'not a second full GPU rerun'):
        assert phrase in text, f'Missing reviewed report claim: {phrase}'
    for name, expected in visual['page_sha256'].items():
        assert sha(ROOT / 'tmp/pdfs/final-review' / name) == expected

    requirements = [
        {'requirement': 'Experimentally grounded CA2-centered circuit and explicit defaults', 'evidence': ['circuit-source-audit.json', 'export-consistency-audit.json', 'nominal-parameter-classification.json', 'methods.txt'], 'verified': '14 exported types and87connectionrows;51implementedrows including25default flags; missing pathways and fitted point-neuron parameters disclosed.'},
        {'requirement': 'Installed simulator executes on the local NVIDIA GPU', 'evidence': ['backend-source-provenance.json', str(runtime_log.relative_to(ROOT))], 'verified': 'Archived source commit, all3library hashes and modified source hashes match; runtime log records1GPU/0CPU; native architecture/runtime limitations disclosed.'},
        {'requirement': 'Defined task, frozen protocol, state reset and matched interventions', 'evidence': ['frozen-task-protocol.json', 'nominal-experiment-audit.json', 'extended-experiment-audit.json', 'readout-training-scope.json'], 'verified': '14frozenhashes unchanged;80nominalcore/240readouts plus208extendedcore/1344readouts independently audited. Every replay stream reconstructed; configurations and complete raw outputs checked.', 'limit': 'Aggregate graph signatures are not individual-edge hashes; output blocking is not a whole-cell lesion.'},
        {'requirement': 'Held-out primary/secondary measures, input control and null results', 'evidence': ['reset-task-results.json', 'secondary-voltage-results.json', 'generalization-results.json'], 'verified': 'Five network seeds; primary chance outcomes retained;10nominal and30unseen input controls100%/countcontrol50%; paired bootstrap and1000label-permutation diagnostics retained.'},
        {'requirement': 'Response dynamics and population comparisons', 'evidence': ['response-dynamics-results.json', 'context-response-results.json', 'generalization-results.json', 'figures/response-dynamics.png'], 'verified': 'Rates, latencies, responsive fractions, similarity and class separation cover all5CA2types; silent populations retained as missing where undefined.'},
        {'requirement': 'Sensitivity to parameters and numerical precision', 'evidence': ['sensitivity-results.json', 'variant-precision-results.json', 'readout-precision40vs80-results.json'], 'verified': 'All prospectively specified parameter/output/precision variants and matched controls completed;7/8spot checks meet tolerance; failed gain150case retained.', 'limit': 'Core parameter screens use one network; voltage effects are conditional and numerically fragile.'},
        {'requirement': 'Unseen input patterns and timing with fixed readout', 'evidence': ['generalization-results.json', 'generalization-scientific-review.json'], 'verified': '120newcoretrials/360readouts across5networks; nominal centroids never retrained on new test data;6cases retain nulls and selective voltage generalization.'},
        {'requirement': 'Physiology calibration distinguished from validation', 'evidence': ['pyramidal-calibration-results.json', 'pyramidal-train-validation-results.json', 'ca1-adequacy-results.json'], 'verified': 'Calibration targets and held-out train checks archived; failed defaults and mismatched CA1subthreshold check disclosed.', 'limit': 'CA1biological adequacy remains unestablished; no animal function claim follows.'},
        {'requirement': 'Reproducible configuration, raw records, analyses and scientific figures', 'evidence': ['artifact-manifest.json', 'REPRODUCE.txt', 'reproduction-copy-validation.json'], 'verified': f'{inventory["file_count"]} inventoried files rehashed; isolated fresh copy verified inputs, frozen hashes and dependencies.', 'limit': 'No second full GPU rerun; rerun uses this archived implementation and the installed CUDA-compatible runtime.'},
        {'requirement': 'Inspectable report and bounded scientific conclusion', 'evidence': ['output/pdf/ca2-scientific-experiment.pdf', 'report-visual-review.json'], 'verified': 'Seven rendered pages reviewed; effect sizes and limitations agree with actual analyses; reports numerical failure and downstream biological-validation limits.'},
    ]
    out = {'objective': 'Reproducible, experimentally grounded CA2-centered circuit experiment with scientifically interpretable, evidence-bounded results', 'reviewed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'completion_supported': True, 'requirements': requirements, 'nominal_input_positive_controls': controls, 'inventory_sha256': sha(ROOT / 'artifact-manifest.json'), 'all_inventoried_files_rehashed': inventory['file_count'], 'total_verified_core_runs': 288, 'total_verified_readouts': 1584, 'unresolved_scientific_limits': ['One gain150numerical spot check fails tolerance.', 'CA1downstream assay lacks matched biological validation.', 'CA3-associated suppression reverses when fitted inhibitory gain is halved.', 'Voltage effects depend on assumptions and input conditions.', 'No social learning, behavioral validation or general animal function established.'], 'completion_meaning': 'The planned controlled experiment, checks and bounded report are complete. Failed biological/numerical tests are results and limitations, not successes.'}
    (ROOT / 'completion-audit.json').write_text(json.dumps(out, indent=2) + '\n')
    print(f'Completion supported for {len(requirements)} requirements; {inventory["file_count"]} files rehashed; scientific failures explicitly retained.')


if __name__ == '__main__':
    main()
