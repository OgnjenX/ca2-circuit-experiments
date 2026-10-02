from pathlib import Path
import shutil,json,hashlib,math
root=Path(__file__).resolve().parent
source=root.parent/'ca2-simulation/rebuild/CARLsim4-feat-meansdSTPPost_hc'
target=root/'simulator-reversal-variant'
assert not target.exists()
shutil.copytree(source,target,ignore=shutil.ignore_patterns('*.o','*.a','.git','doc','projects','tools'))
files=['carlsim/kernel/src/snn_cpu_module.cpp','carlsim/kernel/src/gpu_module/snn_gpu_module.cu'];patches=[]
for rel in files:
 p=target/rel;s=p.read_text();assert s.count('(v + 70.0f)')==1
 oldhash=hashlib.sha256(s.encode()).hexdigest()
 s='#ifndef CA2_EXPERIMENT_GABAA_REVERSE_MAGNITUDE\n#define CA2_EXPERIMENT_GABAA_REVERSE_MAGNITUDE 70.0f\n#endif\n'+s.replace('(v + 70.0f)','(v + CA2_EXPERIMENT_GABAA_REVERSE_MAGNITUDE)')
 p.write_text(s);patches.append({'path':rel,'original_sha256':oldhash,'patched_sha256':hashlib.sha256(s.encode()).hexdigest()})
# Both numerical backends receive the same compile-time constant. Default remains original 70mV.
p=target/'carlsim/configure.mk'
with p.open('a') as f:f.write('\n# Experiment-only sensitivity parameter; original simulator is preserved.\nCA2_GABAA_MAGNITUDE ?= 70.0f\nCXXFL += -DCA2_EXPERIMENT_GABAA_REVERSE_MAGNITUDE=$(CA2_GABAA_MAGNITUDE)\nNVCCFL += -DCA2_EXPERIMENT_GABAA_REVERSE_MAGNITUDE=$(CA2_GABAA_MAGNITUDE)\n')
ecl=-8.314462618*306.15/96485.33212*1000*math.log(133.5/7)
(root/'inhibition-revision-design.json').write_text(json.dumps({'status':'exploratory diagnosis before functional protocol freeze','reason':'Default full-core single-pulse CA3 inhibitory voltage difference -0.266mV versus published -13.8±2.4mV; excitatory amplitude matches calibration.','source':'https://pmc.ncbi.nlm.nih.gov/articles/PMC2905041/','reversal_candidates_mV':[-70,-75,-77.8,-80],'nominal_candidate_mV':-77.8,'recipe_ECl_calculation_mV':ecl,'recipe':'33C; extracellular Cl 133.5mM from NaCl125,KCl2.5,CaCl2(2*2),MgCl2(2*1); pipette Cl7mM from KCl5,NaCl2.','limitation':'ECl calculated from nominal recording solutions is not a measured CA2 GABAa reversal. Bicarbonate permeability, ionic activities and junction potentials can alter the effective reversal; use a sensitivity range, not a claim of measurement. This is an experiment-specific model revision; not a Hippocampome export parameter.','gain_plan':'Explore aggregate inhibitory gain only against published single-pulse CA3 inhibitory response, retaining input count1940 selected against excitatory amplitude. Do not fit functional task or use LIII inhibition as a MEC LII target. Large required gain counts as a model-adequacy warning.','independent_checks':['SC five-pulse100Hz intact inhibition versus blocked','MEC LII train qualitative response, with no fabricated numerical inhibitory target','RK4 10 versus20 substeps on evoked responses','reversal sensitivity -75,-80mV','multiple independent network seeds'],'patches':patches},indent=2))
print(target)
