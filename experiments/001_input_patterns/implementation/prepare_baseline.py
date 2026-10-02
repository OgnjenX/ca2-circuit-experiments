from pathlib import Path
import csv,re,json,hashlib
root=Path(__file__).resolve().parent
prior=root.parent/'ca2-simulation'
rows=list(csv.DictReader((prior/'CA2_conn_parameters09-30-2026_13_09_54.csv').open()))
neurons=list(csv.DictReader((prior/'CA2_neuron_parameters09-30-2026_13_09_54.csv').open()))
def symbol(s): return s.replace(' ','_').replace('-','_')
lookup={(symbol(r['Presynaptic Neuron Type']),symbol(r['Postsynaptic Neuron Type'])):r for r in rows}
old=(prior/'rebuild/model/generateCONFIGStateSTP.h').read_text()
changes=[]
def replace(m):
 r=lookup[m[1],m[2]];changes.append({'pre':m[1],'post':m[2],'old':float(m[3]),'fresh':float(r['Connection Probability'])})
 return m[0].replace(m[3]+'f',r['Connection Probability']+'f')
new=re.sub(r'sim.connect\((\w+), (\w+), "random", RangeWeight\(0.0f, 1.0f, 2.0f\), ([0-9.eE+-]+)f,',replace,old)
assert len(changes)==25
# Audit the rest of each CSV connection against original generated values.
for (pre,post),r in lookup.items():
 block=re.search(r'sim.setSTP\('+pre+', '+post+r', true,(.*?)\);',old,re.S)[1]
 for field,api in [('u','STPu'),('tau_f','STPtauU'),('tau_r','STPtauX'),('tau_d','STPtdAMPA' if r['Source Subregion']=='CA2' and pre=='CA2_Pyramidal' else 'STPtdGABAa')]:
  val=float(re.search(api+r'\(([0-9.eE+-]+)f',block)[1]); assert abs(val-float(r[field]))<1e-10,(pre,post,field)
 block=re.search(r'sim.connect\('+pre+', '+post+r',(.*?)\);',old,re.S)[1]
 assert abs(float(re.search(r'SYN_PLASTIC, ([0-9.eE+-]+)f',block)[1])-float(r['g']))<1e-10
 assert int(re.search(r'RangeDelay\((\d+)\)',block)[1])==int(r['Synaptic Delay'])
for r in neurons:
 s=symbol(r['Neuron Type']); params=re.search(r'sim.setNeuronParameters\('+s+r',(.*?)\);',old,re.S)[1]
 nums=[float(x) for x in params.split(',')]
 cols=['Izh C','Izh k','Izh Vr','Izh Vt','Izh a','Izh b','Izh Vpeak','Izh Vmin','Izh d','Refractory Period']
 assert nums==[float(r[c]) for c in cols]
 assert re.search(r'sim.createGroup\("'+s+r'", (\d+)',old)[1]==r['Population Size']
(root/'model/old_config.h').write_text(old)
(root/'model/fresh_config.h').write_text(new)
(root/'model/setup.h').write_text((prior/'rebuild/model/generateSETUPStateSTP.h').read_text())
(root/'parameter-audit.json').write_text(json.dumps({'changes':changes,'other_exported_fields':'matched exactly against packaged source','default_flags':{'neurons':{r['Neuron Type']:r['CARLsim_default'] for r in neurons},'connections':{r['Presynaptic Neuron Type']+' -> '+r['Postsynaptic Neuron Type']:r['CARLsim_default'] for r in rows}},'warning':'Connection default flags are row-level; do not imply every parameter is a direct measurement. Export does not distinguish dorsal/ventral CA2 or certify matched mouse experiments.'},indent=2))
print('Audited 5 neuron types and 25 connections; generated fresh and old configurations.')
