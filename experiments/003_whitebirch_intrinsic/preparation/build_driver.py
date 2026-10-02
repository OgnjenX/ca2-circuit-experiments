"""Compile-only by default; execution requires a committed, ready preregistration.

Builds a native observer harness against the corrected, unchanged static backend.
The executable includes unchanged carlsim.cpp solely to expose its internal SNN
pointer; ordinary archive extraction must leave carlsim-cpp.o unselected.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ASSAY = HERE.parent
ROOT = ASSAY.parents[1]
DEFAULT_BACKEND = Path('/home/ognjen/Documents/Codex/2026-10-02/task/backend-v2/backend')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def command(args, **kwargs):
    return subprocess.run(list(map(str,args)), check=True, text=True, capture_output=True, **kwargs)


def build(backend, workspace):
    backend = backend.resolve()
    library = backend/'libcarlsim.a.4.0.0'
    model = json.loads((ASSAY/'model_configuration.json').read_text())
    csv_path = ROOT/model['parameter_file']
    if digest(csv_path) != model['parameter_file_sha256']:
        raise ValueError('Archived parameter file hash mismatch')
    row = next(r for r in csv.DictReader(csv_path.open()) if r['Neuron Type']=='CA2 Pyramidal')
    if row != model['archived_row']:
        raise ValueError('Configuration does not match exact archived CSV row')
    sources = {str(p.relative_to(backend)):digest(p) for p in sorted((backend/'carlsim').rglob('*'))
               if p.is_file() and p.suffix in {'.cpp','.cu','.h'}}
    library_hash = digest(library)
    workspace.mkdir(parents=True, exist_ok=False)
    names = {'C':'Izh C','K':'Izh k','VR':'Izh Vr','VT':'Izh Vt','A':'Izh a',
             'B':'Izh b','VPEAK':'Izh Vpeak','VMIN':'Izh Vmin','D':'Izh d'}
    header = ''.join(f'constexpr float ASSAY_{n} = {float(row[k])!r}f;\n' for n,k in names.items())
    header += f'constexpr int ASSAY_REFRACTORY = {int(row["Refractory Period"])};\n'
    header += f'constexpr double ASSAY_U_HOLD = {model["u_hold_pA"]!r};\n'
    header += f'constexpr double ASSAY_I_HOLD = {model["I_hold_pA"]!r};\n'
    header += f'constexpr const char* ASSAY_LIBRARY_SHA256 = "{library_hash}";\n'
    header += f'constexpr const char* ASSAY_HARNESS_SHA256 = "{digest(HERE / "gpu_harness.cpp")}";\n'
    (workspace/'assay_config.h').write_text(header)
    compiler = shutil.which('g++')
    nvcc = shutil.which('nvcc')
    if not compiler or not nvcc:
        raise ValueError('Native g++ and nvcc toolchain required')
    includes = [backend/'carlsim/interface/inc',backend/'carlsim/interface/src',
                backend/'carlsim/kernel/inc',backend/'carlsim/monitor',workspace]
    executable = workspace/'gpu_harness'
    build_command = [compiler,'-std=c++11','-O2','-g','-D__CUDA12__',
                     *[f'-I{p}' for p in includes],HERE/'gpu_harness.cpp',library,
                     '-Wl,--wrap=cudaMemcpy',f'-Wl,-Map,{workspace / "link.map"}',
                     '-lcudart','-lcurand','-lpthread','-ldl','-o',executable]
    result = subprocess.run(list(map(str,build_command)),text=True,capture_output=True)
    (workspace/'compile.log').write_text(result.stdout+result.stderr)
    record = {'kind':'compile-only native GPU preparation','simulation_executed':False,
              'backend':str(backend),'library':str(library),'library_sha256':library_hash,
              'model_configuration_sha256':digest(ASSAY/'model_configuration.json'),
              'parameter_csv_sha256':digest(csv_path),'harness_sha256':digest(HERE/'gpu_harness.cpp'),
              'driver_sha256':digest(__file__),'header_sha256':digest(workspace/'assay_config.h'),
              'backend_source_sha256':sources,'command':list(map(str,build_command)),
              'compiler':command([compiler,'--version']).stdout,
              'compiler_sha256':digest(Path(compiler).resolve()),
              'nvcc':command([nvcc,'--version']).stdout,'nvcc_sha256':digest(Path(nvcc).resolve()),
              'compile_exit_code':result.returncode,
              'initial_state_float32':'V/nextV=-70;u=float(analytic exact-CSV hold);refcounter=0;curSpike=false',
              'instrumentation':'--wrap=cudaMemcpy: real existing DtoD copy first, read-only synchronous scalar DtoH snapshots afterwards',
              'mode':'actual GPU_MODE, GPU_CORES, one neuron; fresh process/simulator per sweep'}
    if result.returncode == 0:
        link_map = (workspace/'link.map').read_text()
        # Including carlsim.cpp resolves interface symbols, so its archive object must not be selected.
        if f'{library}(carlsim-cpp.o)' in link_map:
            raise ValueError('Duplicate interface archive object was selected')
        record['archive_interface_object_selected'] = False
        record['executable_sha256'] = digest(executable)
        dependencies = command(['ldd',executable]).stdout
        record['linked_dependencies'] = dependencies
        record['linked_dependency_sha256'] = {}
        for line in dependencies.splitlines():
            parts = line.split()
            candidates = [Path(part) for part in parts if part.startswith('/')]
            for path in candidates:
                if path.is_file():
                    record['linked_dependency_sha256'][str(path.resolve())] = digest(path.resolve())
        record['wrapper_symbols'] = command(['nm',executable]).stdout.splitlines()
        record['wrapper_symbols'] = [x for x in record['wrapper_symbols']
                                     if x.split()[-1].startswith(('__wrap_cudaMemcpy','cudaMemcpy@'))]
    if digest(library)!=library_hash or any(digest(backend/n)!=h for n,h in sources.items()):
        raise ValueError('Backend source or library changed during compile')
    (workspace/'build_record.json').write_text(json.dumps(record,indent=2)+'\n')
    if result.returncode:
        raise RuntimeError(f'Compile failed; inspect {workspace / "compile.log"}')
    return executable


def float32(value):
    return struct.unpack('f',struct.pack('f',value))[0]


def verify_runtime(executable, workspace, manifest):
    """Bind existing artifacts to committed identities before any native process."""
    record_path=workspace/'build_record.json'
    frozen_record=ASSAY/'revisions/002/build_record.json'
    if record_path.read_bytes()!=frozen_record.read_bytes():
        raise ValueError('Workspace build record differs from frozen build record')
    record=json.loads(record_path.read_text())
    pins=manifest['runtime_pins']
    for key in ('library_sha256','backend_source_sha256','header_sha256',
                'executable_sha256','harness_sha256','driver_sha256'):
        if record.get(key)!=pins.get(key):
            raise ValueError(f'Compiled record differs from runtime pin: {key}')
    if record['compile_exit_code']!=0 or record.get('archive_interface_object_selected') is not False:
        raise ValueError('Native link was not verified')
    if Path(record['command'][-1]).resolve()!=executable.resolve():
        raise ValueError('Executable is not the frozen build workspace artifact')
    for path,key in ((executable,'executable_sha256'),(workspace/'assay_config.h','header_sha256'),
                     (HERE/'gpu_harness.cpp','harness_sha256'),(HERE/'build_driver.py','driver_sha256'),
                     (Path(record['library']),'library_sha256')):
        if digest(path)!=pins[key]:
            raise ValueError(f'Runtime artifact bytes differ: {path}')
    backend=Path(record['backend'])
    actual_sources={str(p.relative_to(backend)):digest(p) for p in sorted((backend/'carlsim').rglob('*'))
                    if p.is_file() and p.suffix in {'.cpp','.cu','.h'}}
    if actual_sources!=pins['backend_source_sha256']:
        raise ValueError('Backend source/header set differs from frozen source map')
    for path,expected in record['linked_dependency_sha256'].items():
        if digest(path)!=expected:
            raise ValueError(f'Linked runtime dependency differs: {path}')
    if command(['ldd',executable]).stdout!=record['linked_dependencies']:
        # Address randomization changes ldd addresses; compare resolved path sets below.
        loaded={str(Path(part).resolve()) for line in command(['ldd',executable]).stdout.splitlines()
                for part in line.split() if part.startswith('/')}
        if loaded!=set(record['linked_dependency_sha256']):
            raise ValueError('Dynamic dependency resolution differs from frozen build')
    for name in ('LD_PRELOAD','LD_LIBRARY_PATH','LD_AUDIT'):
        if os.environ.get(name):
            raise ValueError(f'Dynamic loader override is incompatible with frozen runtime: {name}')
    return record


def check_metadata(stdout, steps, current, pins):
    records=[json.loads(line) for line in stdout.splitlines() if line.startswith('{')]
    if len(records)!=1:
        raise ValueError('Native stdout must contain exactly one configuration JSON record')
    actual=records[0]
    model=json.loads((ASSAY/'model_configuration.json').read_text())
    hold=float32(model['I_hold_pA'])
    expected={'mode':'GPU_MODE','steps_per_ms':steps,'step_current_pA':current,
              'holding_float32_pA':hold,'pulse_float32_pA':float32(hold+float32(current)),
              'initial_u_float32_pA':float32(model['u_hold_pA']),
              'parameters_float32':{k:float32(v) for k,v in model['parameters'].items()},
              'dt_float32_ms':float32(1./steps),
              'refractory_period':int(model['archived_row']['Refractory Period']),
              **{k:pins[k] for k in ('library_sha256','header_sha256','harness_sha256')}}
    if actual!=expected:
        raise ValueError(f'Native configuration differs from freeze: actual={actual}, expected={expected}')
    return actual


def execute(executable, workspace, frozen_commit):
    head = command(['git','rev-parse','HEAD'],cwd=ROOT).stdout.strip()
    if not frozen_commit or frozen_commit != head:
        raise ValueError('Explicit frozen commit must equal current HEAD')
    manifest=json.loads((ASSAY/'revisions/002/preregistration_manifest.json').read_text())
    relatives=set(manifest['sha256'])|{'revisions/002/preregistration_manifest.json',
                                     'revisions/002/build_record.json'}
    for relative in relatives:
        source = ASSAY/relative
        committed=subprocess.run(['git','show',f'{head}:{source.relative_to(ROOT)}'],
                                 cwd=ROOT,check=True,capture_output=True).stdout
        if committed != source.read_bytes():
            raise ValueError(f'Uncommitted production input: {relative}')
        if relative in manifest['sha256'] and digest(source)!=manifest['sha256'][relative]:
            raise ValueError(f'Frozen source checksum differs: {relative}')
    verify_runtime(executable,workspace,manifest)
    command([sys.executable,ASSAY/'revisions/002/verify_stages.py','--require-numerical-ready',
             '--build-record',workspace/'build_record.json'],cwd=ROOT)
    outputs = workspace/'traces'
    outputs.mkdir()
    env = dict(os.environ,CA2_WHITEBIRCH_FROZEN_RUN_AUTHORIZED=head,
               CA2_WHITEBIRCH_HEADER_SHA256=digest(workspace/'assay_config.h'))
    for steps in (20,40,80):
        for current in range(0,1001,100):
            # Recheck artifact identities before each process, not only the first sweep.
            verify_runtime(executable,workspace,manifest)
            prefix=outputs/f'rk{steps}_step{current}'
            native_command=[str(x) for x in (executable,'--run-frozen',steps,current,str(prefix)+'.csv')]
            result=subprocess.run(native_command,cwd=workspace,env=env,text=True,capture_output=True)
            Path(str(prefix)+'.stdout').write_text(result.stdout)
            Path(str(prefix)+'.stderr').write_text(result.stderr)
            run_record={'command':native_command,'frozen_commit':head,'exit_code':result.returncode,
                        'metadata_matches_freeze':False,'failure':None}
            try:
                if result.returncode:
                    raise RuntimeError(f'Native process exited with status {result.returncode}')
                run_record['metadata']=check_metadata(result.stdout,steps,current,manifest['runtime_pins'])
                run_record['metadata_matches_freeze']=True
            except Exception as error:
                run_record['failure']=str(error)
            Path(str(prefix)+'.exit.json').write_text(json.dumps(run_record,indent=2)+'\n')
            print(f'GPU sweep RK{steps}, {current} pA: native exit {result.returncode}, '
                  f'metadata verified={run_record["metadata_matches_freeze"]}',flush=True)
            if run_record['failure']:
                raise RuntimeError(f'Preserved failed native run at {prefix}: {run_record["failure"]}')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend',type=Path,default=DEFAULT_BACKEND)
    parser.add_argument('--workspace',type=Path,required=True,
                        help='Fresh ignored data/workspaces directory or /tmp directory')
    modes=parser.add_mutually_exclusive_group()
    modes.add_argument('--execute',action='store_true',help='Build first, then require exact frozen artifact pins')
    modes.add_argument('--execute-existing',action='store_true',help='Use the already frozen compiled workspace; skip compilation')
    parser.add_argument('--frozen-commit')
    args=parser.parse_args()
    if args.execute_existing:
        executable=args.workspace.resolve()/'gpu_harness'
    else:
        executable=build(args.backend,args.workspace.resolve())
        print(f'Compiled without neuron execution: {executable}',flush=True)
    if args.execute or args.execute_existing:
        execute(executable,args.workspace.resolve(),args.frozen_commit)
