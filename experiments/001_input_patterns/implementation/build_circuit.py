from pathlib import Path
import csv,json,re
root=Path(__file__).resolve().parent;src=root/'revised-source-export'
neuron={r['Neuron Type']:r for r in csv.DictReader(next(src.glob('*neuron*')).open())}
conn=list(csv.DictReader(next(src.glob('*conn*')).open()))
def sym(s):return s.replace(' ','_').replace('-','_')
def connection(r):
 pre,post=sym(r['Presynaptic Neuron Type']),sym(r['Postsynaptic Neuron Type']);exc=neuron[r['Presynaptic Neuron Type']]['E/I']=='e'
 tdA=r['tau_d'] if exc else '5.0';tdG='6.0' if exc else r['tau_d']
 return f'''sim.connect({pre}, {post}, "random", RangeWeight(0.0f,1.0f,2.0f), {r['Connection Probability']}f, RangeDelay({r['Synaptic Delay']}), RadiusRF(-1), SYN_PLASTIC, {r['g']}f, 0.0f);
sim.setSTP({pre}, {post}, true, STPu({r['u']}f,0), STPtauU({r['tau_f']}f,0), STPtauX({r['tau_r']}f,0), STPtdAMPA({tdA}f,0), STPtdNMDA(150.0f,0), STPtdGABAa({tdG}f,0), STPtdGABAb(150.0f,0), STPtrNMDA(0.0f,0), STPtrGABAb(0.0f,0));'''
# The existing audited CA2 network is retained at full counts.
core=(root/'model/fresh_config.h').read_text();core=re.sub(r'sim.setNeuronMonitor\(.*?\);','',core)
core+='\nint MEC_LII_Stellate=sim.createSpikeGeneratorGroup("MEC_LII_Stellate",10818,EXCITATORY_NEURON);\n'
core+='int CA3_Pyramidal=sim.createSpikeGeneratorGroup("CA3_Pyramidal",4096,EXCITATORY_NEURON);\n'
core_edges=[r for r in conn if r['Presynaptic Neuron Type'] in ['MEC LII Stellate','CA3 Pyramidal'] and r['Postsynaptic Neuron Type'].startswith('CA2 ')]
core=re.sub(r'sim.connect\((CA2_(?:Basket|Wide_Arbor_Basket|Bistratified|SP_SR)),.*?\);',lambda m:'core_inhibitory_connections.push_back('+m[0][:-1]+');',core,flags=re.S)
# Capture target-specific handles without changing any connection specification.
core=re.sub(r'(core_inhibitory_connections.push_back\(sim.connect\(CA2_(?:Basket|Wide_Arbor_Basket|Bistratified|SP_SR),\s*CA2_Pyramidal,.*?\);)',lambda m:m[0]+'\ncore_pyramidal_inhibitory_connections.push_back(core_inhibitory_connections.back());',core,flags=re.S)
core+='\n'.join(connection(r) for r in core_edges)
core+='\nNeuronMonitor* monitor_CA2=sim.setNeuronMonitor(CA2_Pyramidal, "DEFAULT");\n'
(root/'model/core_config.h').write_text(core)
# Feedforward assay: CA1 target sample and source-count inhibitory populations.
readout=''
for name,count in [('CA1 Pyramidal',128),('CA1 Basket',819),('CA1 Bistratified',1962)]:
 r=neuron[name];s=sym(name);typ='EXCITATORY_NEURON' if r['E/I']=='e' else 'INHIBITORY_NEURON'
 readout+=f'int {s}=sim.createGroup("{s}",{count},{typ},0,GPU_CORES);\n'
 cols=['Izh C','Izh k','Izh Vr','Izh Vt','Izh a','Izh b','Izh Vpeak','Izh Vmin','Izh d','Refractory Period']
 readout+=f'sim.setNeuronParameters({s},'+','.join(r[c] for c in cols)+');\n'
for name,count in [('CA2 Pyramidal',18956),('CA2 Basket',105),('CA2 Wide-Arbor Basket',147),('CA2 Bistratified',79),('CA2 SP-SR',94),('CA3 Pyramidal',4096)]:
 typ='EXCITATORY_NEURON' if neuron[name]['E/I']=='e' else 'INHIBITORY_NEURON';s=sym(name)
 readout+=f'int {s}=sim.createSpikeGeneratorGroup("{s}",{count},{typ});\n'
readout_edges=[r for r in conn if r['Postsynaptic Neuron Type'] in ['CA1 Pyramidal','CA1 Basket','CA1 Bistratified'] and (r['Presynaptic Neuron Type'].startswith(('CA2 ','CA3 ')) or r['Presynaptic Neuron Type'] in ['CA1 Basket','CA1 Bistratified'])]
readout+='\n'.join(connection(r) for r in readout_edges)
(root/'model/readout_config.h').write_text(readout)
(root/'circuit-construction.json').write_text(json.dumps({'core_edges':core_edges,'readout_edges':readout_edges,'boundary':'Prescribed open-loop afferents; no MEC or CA3 feedback; CA1 is a feedforward target assay with 128 pyramidal target cells plus full selected inhibitory populations, not complete CA1. No CA1 pyramidal feedback is represented. CA3 prescribed source pool contains 4096 afferents; stimulated subsets are specified in each input fixture, and unrepresented afferents are assumed silent. Exported conductances are unchanged at inhibitory_gain=1; diagnostic runs explicitly record any aggregate inhibitory gain. No connection replacement.','MEC_identity':'MEC LII Stellate only; does not represent LEC social information','synaptic_convention':'Reuse packaged CARLsim factor conductance, initial weight1, pair-specific STP and AMPA/GABAa only; SYN_PLASTIC does not imply an enabled learning rule.'},indent=2))
print('Generated core and readout configurations from',len(core_edges),'and',len(readout_edges),'exported edges.')

# Isolated EPSP assay: an unconnected target sample under GABA blockade.
r=neuron['CA2 Pyramidal'];cols=['Izh C','Izh k','Izh Vr','Izh Vt','Izh a','Izh b','Izh Vpeak','Izh Vmin','Izh d','Refractory Period']
cal='int CA2_Pyramidal=sim.createGroup("CA2_Pyramidal",128,EXCITATORY_NEURON,0,GPU_CORES);\n'
cal+='sim.setNeuronParameters(CA2_Pyramidal,'+','.join(r[c] for c in cols)+');\n'
cal+='int MEC_LII_Stellate=sim.createSpikeGeneratorGroup("MEC_LII_Stellate",10818,EXCITATORY_NEURON);\nint CA3_Pyramidal=sim.createSpikeGeneratorGroup("CA3_Pyramidal",4096,EXCITATORY_NEURON);\n'
cal+='\n'.join(connection(r) for r in core_edges if r['Postsynaptic Neuron Type']=='CA2 Pyramidal')
cal+='\nNeuronMonitor* monitor_CA2=sim.setNeuronMonitor(CA2_Pyramidal,"DEFAULT");\n'
(root/'model/calibration_config.h').write_text(cal)
