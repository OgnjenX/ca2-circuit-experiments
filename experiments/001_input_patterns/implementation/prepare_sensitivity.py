from pathlib import Path
import shutil,csv,re,json,hashlib
r=Path(__file__).resolve().parent;dest=r/'model/sensitivity';assert not dest.exists();(dest/'src').mkdir(parents=True)
for name in ['core_config.h','readout_config.h','calibration_config.h','setup.h']:shutil.copy2(r/'model'/name,dest/name)
rows=list(csv.DictReader(next((r/'revised-source-export').glob('*conn*')).open()))
edges=[row for row in rows if row['Presynaptic Neuron Type']=='CA2 Pyramidal' and row['Postsynaptic Neuron Type'] in ['CA1 Pyramidal','CA1 Basket','CA1 Bistratified'] and row['CARLsim_default']=='Y'];assert len(edges)==3
p=dest/'readout_config.h';s=p.read_text()
for row in edges:
 target=row['Postsynaptic Neuron Type'].replace(' ','_');pattern=rf'sim.connect\(CA2_Pyramidal, {target},.*?;'
 matches=re.findall(pattern,s);assert len(matches)==1;s=s.replace(matches[0],'default_output_connections.push_back('+matches[0][:-1]+');')
p.write_text(s)
s=(r/'model/src/circuit.cpp').read_text().replace('argc!=6&&argc!=7&&argc!=8','argc!=6&&argc!=7&&argc!=8&&argc!=9').replace('[all|pyramidal]','[all|pyramidal] [default_output_gain]').replace('argc==8?argv[7]','argc>=8?argv[7]').replace('std::srand(seed);','float output_gain=argc==9?std::stof(argv[8]):1.0f;\n if(output_gain<0||output_gain>10)return 2;\n std::srand(seed);')
s=s.replace('#include "../readout_config.h"','std::vector<short int> default_output_connections;\n #include "../readout_config.h"').replace('sim.setIntegrationMethod(RUNGE_KUTTA4,steps);sim.setupNetwork();\n for(int group:{CA2_Pyramidal','sim.setIntegrationMethod(RUNGE_KUTTA4,steps);sim.setupNetwork();\n if(output_gain!=1.0f)for(short int id:default_output_connections)sim.scaleWeights(id,output_gain,true);\n for(int group:{CA2_Pyramidal');(dest/'src/circuit.cpp').write_text(s)
for magnitude in [75,80]:
 target=r/f'simulator-reversal-{magnitude}';assert not target.exists();shutil.copytree(r/'simulator-reversal-variant',target,ignore=shutil.ignore_patterns('*.o','*.a','*.a.*'))
 # copytree omits archive symlink too; create correct library link after build in shell.
(r/'sensitivity-implementation.json').write_text(json.dumps({'output_edges':edges,'output_gain_scope':'Scale only these3connectionweights after setup, maintaining topology and allothercouplings. These rows are flaggeddefaultY; varying one effective strength does not cover every default field.','source_configuration':'Frozen nominal source headers copied into model/sensitivity; nominal source untouched.','reversal_builds':'Same CPU/GPU configurable reversal patch as nominal, compile constants75/80mV; original nominallibrary preserved.','source_hashes':{str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()}},indent=2))
print('Sensitivity files prepared;3defaultoutputedges captured.')
