"""Build, calibrate, freeze, run and measure the prospective CA2 benchmark.

Run each stage separately. Calibration sees single pulses only; test trains
cannot run without a committed frozen configuration and matching hashes.
"""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'src'))
from ca2lab.monitors import read_spikes
from ca2lab.slice import measure_epsps, read_voltage_window


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2)+'\n')


def load(path):
    return json.loads(Path(path).read_text())


def commit():
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()


def scientific_files():
    return [HERE/'experiment.py', HERE/'analyze.py', HERE/'protocol.json',
            HERE/'source_targets.json', HERE/'source_audit.json',
            ROOT/'src/ca2lab/slice.py', ROOT/'src/ca2lab/monitors.py',
            ROOT/'models/ca2_slice/src/assay.cpp',
            *sorted((ROOT/'data/hippocampome/2026-10-01').glob('*.csv'))]


def verify_frozen(workspace):
    frozen = load(HERE/'frozen_configuration.json')
    for name, digest in frozen['scientific_file_sha256'].items():
        if sha(ROOT/name) != digest:
            raise ValueError(f'Frozen scientific source changed: {name}')
    if sha(workspace/'build/assay') != frozen['executable_sha256']:
        raise ValueError('Executable changed after freeze')
    if sha(workspace/'build/slice_config.h') != frozen['generated_config_sha256']:
        raise ValueError('Generated configuration changed after freeze')
    if sha(workspace/'build/build_record.json') != frozen['build_record_sha256']:
        raise ValueError('Backend/build identity changed after freeze')
    return frozen


def build(args):
    workspace = args.workspace
    folder = workspace/'build'
    folder.mkdir(parents=True, exist_ok=False)
    tables = ROOT/'data/hippocampome/2026-10-01'
    neurons = list(csv.DictReader(next(tables.glob('*neuron*')).open()))
    connections = list(csv.DictReader(next(tables.glob('*conn*')).open()))
    neuron = next(row for row in neurons if row['Neuron Type'] == 'CA2 Pyramidal')
    edge = next(row for row in connections if row['Presynaptic Neuron Type'] == 'MEC LII Stellate'
                and row['Postsynaptic Neuron Type'] == 'CA2 Pyramidal')
    columns = ['Izh C', 'Izh k', 'Izh Vr', 'Izh Vt', 'Izh a', 'Izh b',
               'Izh Vpeak', 'Izh Vmin', 'Izh d', 'Refractory Period']
    config = f'''int configure_target(CARLsim& sim) {{
    int target = sim.createGroup("CA2_Pyramidal", 128, EXCITATORY_NEURON, 0, GPU_CORES);
    sim.setNeuronParameters(target, {','.join(neuron[c] for c in columns)});
    return target;
}}
int configure_source(CARLsim& sim, int target) {{
    int source = sim.createSpikeGeneratorGroup("MEC_LII_Stellate", 10818, EXCITATORY_NEURON);
    sim.connect(source, target, "random", RangeWeight(0.0f,1.0f,2.0f),
                {edge['Connection Probability']}f, RangeDelay({edge['Synaptic Delay']}),
                RadiusRF(-1), SYN_PLASTIC, {edge['g']}f, 0.0f);
    sim.setSTP(source, target, true, STPu({edge['u']}f,0),
               STPtauU({edge['tau_f']}f,0), STPtauX({edge['tau_r']}f,0),
               STPtdAMPA({edge['tau_d']}f,0), STPtdNMDA(150.0f,0),
               STPtdGABAa(6.0f,0), STPtdGABAb(150.0f,0),
               STPtrNMDA(0.0f,0), STPtrGABAb(0.0f,0));
    return source;
}}
'''
    (folder/'slice_config.h').write_text(config)
    backend = args.backend.resolve()
    library = backend/'libcarlsim.a.4.0.0'
    expected = load(ROOT/'simulators/carlsim4/source.json')['recorded_builds'][0]['library_sha256']
    if sha(library) != expected:
        raise ValueError('Backend is not the recorded nominal library')
    command = ['g++-12', '-std=c++11', '-O2', '-g', '-I'+str(folder),
               '-I'+str(backend/'carlsim/interface/inc'),
               '-I'+str(backend/'carlsim/kernel/inc'), '-I'+str(backend/'carlsim/monitor'),
               str(ROOT/'models/ca2_slice/src/assay.cpp'), str(library),
               '-lcurand', '-lcudart', '-lpthread', '-o', str(folder/'assay')]
    with (folder/'build.log').open('w') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    k, vr, vt, b = (float(neuron[col]) for col in ['Izh k', 'Izh Vr', 'Izh Vt', 'Izh b'])
    holding_v = load(HERE/'protocol.json')['holding_mV']
    holding_i = b*(holding_v-vr)-k*(holding_v-vr)*(holding_v-vt)
    save(folder/'build_record.json', {
        'source_commit': commit(), 'library_sha256': sha(library),
        'executable_sha256': sha(folder/'assay'), 'config_sha256': sha(folder/'slice_config.h'),
        'compiler': subprocess.check_output(['g++-12', '--version'], text=True).splitlines()[0],
        'build_command': [item.replace(str(ROOT), '<repository>').replace(str(backend), '<backend>')
                          for item in command],
        'neuron': neuron, 'edge': edge, 'holding_current_pA': holding_i,
        'holding_formula': 'b*(Vhold-Vr)-k*(Vhold-Vr)*(Vhold-Vt); intrinsic parameters unchanged',
        'implementation': 'Direct MEC input, no recurrence or inhibition; NMDA multiplier zero',
    })
    print('Built assay with recorded backend and unchanged exported intrinsic/STP values.', flush=True)


def simulate(workspace, label, seed, active, frequency, steps, phase_commit):
    directory = workspace/'runs'/label
    if directory.exists():
        if (directory/'measurement.json').exists():
            measurement = load(directory/'measurement.json')
            cfg = load(directory/'configuration.json')
            if (cfg['seed'], cfg['active'], cfg['frequency_Hz'], cfg['steps']) != (seed, active, frequency, steps):
                raise ValueError('Existing run does not match requested configuration')
            if cfg['executable_sha256'] != sha(workspace/'build/assay'):
                raise ValueError('Existing run used a different executable')
            return measurement
        raise ValueError(f'Incomplete previous run: {directory}')
    directory.mkdir(parents=True)
    (directory/'results').mkdir()
    pulses = [5100] if frequency is None else [5100+round(k*1000/frequency) for k in range(5)]
    duration = pulses[-1]+100
    pulse_file = directory/'pulses.txt'
    pulse_file.write_text(''.join(f'{t}\n' for t in pulses))
    cfg = {'seed':seed, 'active':active, 'frequency_Hz':frequency, 'steps':steps,
           'pulses_ms':pulses, 'duration_ms':duration, 'record_start_ms':4950,
           'phase_commit':phase_commit, 'scientific_file_sha256':{str(p.relative_to(ROOT)):sha(p) for p in scientific_files()},
           'executable_sha256':sha(workspace/'build/assay'), 'pulses_sha256':sha(pulse_file)}
    holding = load(workspace/'build/build_record.json')['holding_current_pA']
    save(directory/'configuration.json', cfg)
    before = time.monotonic()
    with (directory/'run.log').open('w') as log:
        outcome = subprocess.run([str(workspace/'build/assay'), str(seed), str(active), str(duration),
                                  str(steps), str(pulse_file), str(holding)], cwd=directory,
                                 stdout=log, stderr=subprocess.STDOUT)
    (directory/'exit-status.txt').write_text(str(outcome.returncode)+'\n')
    if outcome.returncode != 0:
        raise RuntimeError(f'Run failed: {label}; inspect run.log')
    voltage = read_voltage_window(directory/'results/n_CA2_Pyramidal.dat', 128, 4950, duration)
    output = read_spikes(directory/'results/spk_CA2_Pyramidal.dat', 128, duration)
    delivered = read_spikes(directory/'results/spk_MEC_LII_Stellate.dat', 10818, duration)
    expected = {(t,cell) for t in pulses for cell in range(active)}
    actual = {(int(row['t']),int(row['id'])) for row in delivered}
    if actual != expected:
        raise ValueError(f'Input delivery mismatch: {label}')
    measurement = measure_epsps(voltage, 4950, pulses)
    measurement.update({'label':label,'seed':seed,'active':active,'frequency_Hz':frequency,'steps':steps,
                        'spikes':len(output),'input_spikes':len(delivered),
                        'wall_seconds':time.monotonic()-before,
                        'configuration_sha256':sha(directory/'configuration.json'),
                        'raw_sha256':{p.name:sha(p) for p in sorted((directory/'results').glob('*.dat'))}})
    measurement['eligible'] = (len(output)==0 and abs(measurement['baseline_mV']+70)<.05
                               and measurement['max_baseline_drift_mV']<.01)
    save(directory/'measurement.json',measurement)
    print(f"{label}: EPSP1={measurement['mean_peaks_mV'][0]:.3f}, "
          f"ratio={measurement['mean_ratios'][-1]:.3f}, spikes={len(output)}, eligible={measurement['eligible']}", flush=True)
    return measurement


def calibrate(args):
    protocol = load(HERE/'protocol.json')
    record_path = args.workspace/'calibration.json'
    if record_path.exists():
        raise ValueError('Calibration is already recorded; refuse overwrite')
    selections=[]
    for amplitude in protocol['calibration_amplitudes_mV']:
        lo, hi = 1,10818
        candidates=[]
        for iteration in range(protocol['max_calibration_iterations']):
            active = (lo+hi)//2
            results = [simulate(args.workspace,f'cal-n{active}-s{seed}',seed,active,None,
                                protocol['nominal_substeps'],commit()) for seed in protocol['calibration_seeds']]
            if not all(abs(r['baseline_mV']+70)<.05 and r['max_baseline_drift_mV']<.01 for r in results):
                raise ValueError('Holding setup failed; resolve before testing trains')
            peak = float(np.mean([r['mean_peaks_mV'][0] for r in results]))
            candidates.append({'active':active,'mean_peak_mV':peak,'eligible':all(r['eligible'] for r in results)})
            if all(r['eligible'] for r in results) and abs(peak-amplitude)<=protocol['calibration_tolerance_mV']:
                break
            if peak>amplitude or not all(r['eligible'] for r in results):
                hi=active-1
            else:
                lo=active+1
            if lo>hi:
                break
        eligible=[r for r in candidates if r['eligible']]
        if not eligible:
            raise ValueError('No eligible calibration candidate')
        selected=min(eligible,key=lambda r:abs(r['mean_peak_mV']-amplitude))
        if abs(selected['mean_peak_mV']-amplitude)>protocol['calibration_tolerance_mV']:
            raise ValueError('Input recruitment cannot match declared operating level')
        selections.append({'target_amplitude_mV':amplitude,'selected':selected,'candidates':candidates})
        save(args.workspace/'calibration-progress.json',selections)
    save(record_path,{'commit':commit(),'selections':selections,'source':'Figure 4 weak first EPSP mean +/- SEM transferred to Figure 5 APV as an explicit assumption','train_outcomes_seen':False})


def freeze(args):
    destination=HERE/'frozen_configuration.json'
    if destination.exists():
        raise ValueError('Configuration is already frozen')
    calibration=load(args.workspace/'calibration.json')
    if any(args.workspace.glob('runs/test-*')):
        raise ValueError('Train outcome already exists before freeze')
    build_record=load(args.workspace/'build/build_record.json')
    save(destination,{'created_UTC':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                      'pre_freeze_commit':commit(), 'calibration':calibration,
                      'calibration_sha256':sha(args.workspace/'calibration.json'),
                      'analysis_sha256':sha(HERE/'analyze.py'),
                      'scientific_file_sha256':{str(p.relative_to(ROOT)):sha(p) for p in scientific_files()},
                      'executable_sha256':build_record['executable_sha256'],
                      'generated_config_sha256':sha(args.workspace/'build/slice_config.h'),
                      'build_record_sha256':sha(args.workspace/'build/build_record.json'),
                      'build_record':build_record})
    print('Frozen; commit this file before running trains.',flush=True)


def run(args):
    frozen=verify_frozen(args.workspace)
    # Require the frozen file to have entered Git history before test execution.
    subprocess.run(['git','cat-file','-e',f'HEAD:{(HERE/"frozen_configuration.json").relative_to(ROOT)}'],cwd=ROOT,check=True)
    protocol=load(HERE/'protocol.json')
    if protocol['evaluation_seeds'] and set(protocol['evaluation_seeds']) & set(protocol['calibration_seeds']):
        raise ValueError('Calibration and evaluation seeds overlap')
    measurements=[]
    for selection in frozen['calibration']['selections']:
        level=selection['target_amplitude_mV'];active=selection['selected']['active']
        for seed in protocol['evaluation_seeds']:
            for frequency in protocol['frequencies_Hz']:
                label=f'test-a{level}-s{seed}-f{frequency}-rk{protocol["nominal_substeps"]}'
                measurements.append(simulate(args.workspace,label,seed,active,frequency,
                                             protocol['nominal_substeps'],commit()))
            for frequency in protocol['primary_frequencies_Hz']:
                label=f'test-a{level}-s{seed}-f{frequency}-rk{protocol["precision_substeps"]}'
                measurements.append(simulate(args.workspace,label,seed,active,frequency,
                                             protocol['precision_substeps'],commit()))
    save(args.workspace/'measurements.json',{'frozen_sha256':sha(HERE/'frozen_configuration.json'),'runs':measurements})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['build','calibrate','freeze','run'])
    parser.add_argument('--workspace',required=True,type=Path)
    parser.add_argument('--backend',type=Path)
    args=parser.parse_args();args.workspace=args.workspace.resolve()
    if args.stage=='build' and args.backend is None:
        parser.error('build requires --backend')
    {'build':build,'calibrate':calibrate,'freeze':freeze,'run':run}[args.stage](args)


if __name__=='__main__':
    main()
