from pathlib import Path
import json,random
root=Path(__file__).resolve().parent
cases=[]
for pathway,count,target,sem in [('MEC_LII_Stellate',9800,7.4,.9),('CA3_Pyramidal',1940,10.8,2.2)]:
 ids=list(range(10818 if pathway=='MEC_LII_Stellate' else 4096));random.Random(11597).shuffle(ids)
 name=f'{pathway}-{count}';out=root/'stimuli/calibration-refined'/name;out.mkdir(parents=True,exist_ok=True)
 for source in ['MEC_LII_Stellate','CA3_Pyramidal']:(out/(source+'.txt')).write_text(''.join(f'50 {i}\n' for i in sorted(ids[:count])) if source==pathway else '')
 case={'case':name,'pathway':pathway,'active_afferents':count,'target_EPSP_mV':target,'target_SEM_mV':sem,'duration_ms':150,'pulse_time_ms':50,'steps':10,'network_seed':20}
 (out/'configuration.json').write_text(json.dumps(case,indent=2));cases.append(case)
design=json.loads((root/'calibration-v3-design.json').read_text());design['cases']=cases;design['refinement']='Linear interpolation between bracketing coarse-sweep mean EPSPs, rounded to nearby convenient counts. No functional task results used in calibration.';(root/'calibration-refined-design.json').write_text(json.dumps(design,indent=2))
