"""Post-outcome isolated current-step diagnostic; no synaptic input or scoring changes."""
import argparse,json,hashlib,subprocess,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path.insert(0,str(ROOT/'src'))
from ca2lab.slice import read_voltage_window
from ca2lab.monitors import read_spikes
p=argparse.ArgumentParser();p.add_argument('--backend',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();backend=a.backend.resolve();output=a.output.resolve();output.mkdir(parents=True,exist_ok=False)
frozen=json.loads((HERE.parent/'frozen_configuration.json').read_text());n=frozen['build_record']['neuron'];columns=['Izh C','Izh k','Izh Vr','Izh Vt','Izh a','Izh b','Izh Vpeak','Izh Vmin','Izh d','Refractory Period'];params=[float(n[k]) for k in columns];C,k,vr,vt,alpha,b,vpeak,c,d,ref=params;holding=frozen['build_record']['holding_current_pA']
(output/'neuron_config.h').write_text('const float HOLDING='+repr(holding)+'f;\nvoid configure(CARLsim& sim,int target){sim.setNeuronParameters(target,'+','.join(n[c] for c in columns)+');}\n')
subprocess.run(['g++-12','-std=c++11','-O2',f'-I{output}',*[f'-I{backend/x}' for x in ['carlsim/interface/inc','carlsim/kernel/inc','carlsim/monitor']],str(HERE/'current_step.cpp'),str(backend/'libcarlsim.a.4.0.0'),'-lcurand','-lcudart','-lpthread','-o',str(output/'probe')],check=True)
# Independent high-resolution coupled ODE RK4, float64. Initial v=vr,u=0.
def oracle(steps):
    state=np.array([vr,0.],dtype=np.float64);trace=[];h=1/steps
    def rhs(s,current):
        v,u=s;return np.array([(k*(v-vr)*(v-vt)-u+current)/C,alpha*(b*(v-vr)-u)])
    for t in range(5300):
        current=holding+(100 if 5000<=t<5100 else 0)
        for _ in range(steps):
            a1=rhs(state,current);a2=rhs(state+h*a1/2,current);a3=rhs(state+h*a2/2,current);a4=rhs(state+h*a3,current);state+=h*(a1+2*a2+2*a3+a4)/6
        if state[0]>=vpeak:raise ValueError('Diagnostic oracle unexpectedly spiked')
        trace.append(state.copy())
    return np.array(trace)
reference=oracle(80);refined=oracle(160);oracle_error=float(np.max(np.abs(reference-refined)));np.save(output/'oracle80.npy',reference);np.save(output/'oracle160.npy',refined)
results=[];observed={}
for mode in ['cpu','gpu']:
    for steps in [20,40]:
        folder=output/f'{mode}-rk{steps}';folder.mkdir();(folder/'results').mkdir()
        with (folder/'run.log').open('w') as log:subprocess.run([str(output/'probe'),mode,str(steps)],cwd=folder,stdout=log,stderr=subprocess.STDOUT,check=True)
        v=read_voltage_window(folder/'results/n_target.dat',1,0,5300)[0];spikes=read_spikes(folder/'results/spk_target.dat',1,5300);observed[(mode,steps)]=v
        # Voltage monitor records the beginning-of-tick state, as required by original monitor readers.
        expected=np.r_[vr,reference[:-1,0]]
        error=float(np.max(np.abs(v-expected)));row={'mode':mode,'substeps':steps,'spikes':len(spikes),'max_voltage_error_mV':error,'post_warmup_max_error_mV':float(np.max(np.abs(v[4950:]-expected[4950:]))),'baseline_mV':float(v[4999]),'peak_mV':float(v[5000:5100].max()),'pass_diagnostic':len(spikes)==0 and error<.05};results.append(row);print(row,flush=True)
record={'post_outcome_diagnostic_only':True,'scientific_scores_unchanged':True,'scope':'Unchanged exported CA2 intrinsic ODE, no synaptic input, +100pA current for 100ms after 5000ms holding; no resets triggered. Does not validate spike resets or voltage-dependent synaptic coupling.','equations':'C dv/dt=k(v-vr)(v-vt)-u+I; du/dt=a(b(v-vr)-u)','oracle_float64_substeps':[80,160],'oracle_refinement_max_error':oracle_error,'diagnostic_tolerance_mV':.05,'library_sha256':hashlib.sha256((backend/'libcarlsim.a.4.0.0').read_bytes()).hexdigest(),'results':results,'rk20_40_waveform_difference_mV':{mode:float(np.max(np.abs(observed[(mode,20)]-observed[(mode,40)]))) for mode in ['cpu','gpu']},'passed':all(x['pass_diagnostic'] for x in results)}
(output/'results.json').write_text(json.dumps(record,indent=2)+'\n')
