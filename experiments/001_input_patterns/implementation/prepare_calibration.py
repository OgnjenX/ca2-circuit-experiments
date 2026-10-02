from pathlib import Path
import json,random
root=Path(__file__).resolve().parent
cases=[]
for pathway,counts,target,sem in [('MEC_LII_Stellate',[6144,8192,9216,10240],7.4,.9),('CA3_Pyramidal',[1280,1536,1792,2048],10.8,2.2)]:
 ids=list(range(10818 if pathway=='MEC_LII_Stellate' else 4096));random.Random(11597).shuffle(ids)
 for count in counts:
  name=f'{pathway}-{count}';out=root/'stimuli/calibration-v3'/name;out.mkdir(parents=True,exist_ok=True)
  for source in ['MEC_LII_Stellate','CA3_Pyramidal']:(out/(source+'.txt')).write_text(''.join(f'50 {i}\n' for i in sorted(ids[:count])) if source==pathway else '')
  case={'case':name,'pathway':pathway,'active_afferents':count,'target_EPSP_mV':target,'target_SEM_mV':sem,'duration_ms':150,'pulse_time_ms':50,'steps':10,'network_seed':20}
  (out/'configuration.json').write_text(json.dumps(case,indent=2));cases.append(case)
config={'status':'Calibration specification before sweep results','cases':cases,'source':'https://pmc.ncbi.nlm.nih.gov/articles/PMC2905041/','targets':'Figure5: LII-to-CA2 EPSP 7.4±0.9mV at20V with inhibition blocked; Figure3: SC-to-CA2 EPSP10.8±2.2mV at16V with inhibition blocked. n8 and n7; errors SEM.','mapping_limits':'Electrical stimulus voltage has no direct CARLsim equivalent; calibrate stimulated afferent count, retain all intrinsic and synaptic parameters. MEC LII is a subset of the aggregate EC LII pathway. Postsynaptic sample has no inhibitory or recurrent inputs, approximating isolated early EPSP under GABA blockade, not an exact slice preparation.','selection':'Choose tested afferent count with mean peak EPSP nearest target, excluding any case that evokes spikes; if range does not bracket target extend sweep before task freeze. Require independently held-out functional/physiological checks; calibration is not validation.','measurement':'Per-neuron peak voltage from pulse to60ms later minus mean baseline t40-49ms; average128 target cells. Check no target spikes before interpreting EPSP.','provenance':'Calibration controls intervention on stimulated-fiber count only. Target cells use exported fitted point-neuron parameters; they are not experimentally measured replicates.'}
(root/'calibration-v3-design.json').write_text(json.dumps(config,indent=2));print(len(cases),'calibration cases prepared')
