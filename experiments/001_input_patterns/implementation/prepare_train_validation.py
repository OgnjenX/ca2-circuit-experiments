from pathlib import Path
import json
r=Path(__file__).resolve().parent
out=r/'stimuli/physiology-trains';out.mkdir(exist_ok=False)
for pathway,count in [('MEC_LII_Stellate',9800),('CA3_Pyramidal',1940)]:
 src=r/f'stimuli/calibration-refined/{pathway}-{count}';dst=out/pathway;dst.mkdir()
 for name in ['MEC_LII_Stellate','CA3_Pyramidal']:
  original=[line.split() for line in (src/f'{name}.txt').read_text().splitlines()]
  (dst/f'{name}.txt').write_text(''.join(f'{50+10*pulse} {cell}\n' for pulse in range(5) for _,cell in original))
(out/'configuration.json').write_text(json.dumps({'purpose':'Held-out pulse-train physiological check; not used in single-pulse calibration','duration_ms':250,'pulse_times_ms':[50,60,70,80,90],'stimulated_afferents':{'MEC_LII_Stellate':9800,'CA3_Pyramidal':1940},'source':'https://pmc.ncbi.nlm.nih.gov/articles/PMC2905041/','CA3_target':'Figure4: inhibition intact 0/8 CA2 cells spike; inhibition blocked 6/8. Assess qualitative suppression, not exact proportion: point-neuron homogeneity, resting voltages and slice boundaries differ. Paper resting membrane potentials differ under blockade.','MEC_LII_target':'Figure5 establishes strong input and recruitment of inhibition at stronger stimulation, but gives no comparable LII five-pulse spike fraction. Do not apply LIII quantitative targets to MEC LII.','negative_results':'Any validation failure is retained and limits subsequent functional claims.'},indent=2))
print(out)
