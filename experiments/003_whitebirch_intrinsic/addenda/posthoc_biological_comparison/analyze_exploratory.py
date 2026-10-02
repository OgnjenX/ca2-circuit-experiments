"""Explicitly authorized post-hoc description; original failed primary unchanged."""
import csv,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ASSAY=HERE.parents[1]
sys.path.insert(0,str(ASSAY/'revisions/002'))
from analyze import scoring_bounds

def main():
    native=ASSAY/'results/numerical_checks.json';target=ASSAY/'revisions/002/target_data.json'
    n=json.loads(native.read_text());t=json.loads(target.read_text())
    assert n['passed'] is False
    records={r['metadata']['step_current_pA']:r for r in n['records'] if r['metadata']['steps_per_ms']==80}
    counts={i:r['crossing_audit']['raw_counts']['pulse'] for i,r in records.items()}
    raw=scoring_bounds(counts,t['rows'])
    for row in raw['rows']:
        r=records[row['current_pA']]
        row['whole_recording_count']=r['crossing_audit']['whole_trace_raw']
        row['postpulse_count']=r['crossing_audit']['raw_counts']['post']
    result={'status':'Explicitly authorized POST-HOC exploratory comparison; original primary numerical gate failed and remains gated','authorization':'User requested actual current biological agreement after reviewing original failed numerical result; no preregistered validation claim','source_result_commit':'ae666025e3597b66da0aab4b7a6fd9a47252147e','primary_numerical_pass':False,'rows':raw['rows'],'exploratory_all_ten_conditional_bounds':raw['primary_all_current_bounds'],'exploratory_nine_visible_mean_summary':raw['secondary_visible_mean_point_summary'],'input_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [native,target]},'frozen_100pA_interval_unchanged':[0,1.2]}
    result['exploratory_all_ten_conditional_bounds']['interpretation']='POST-HOC conditional figure-reading bounds, not confidence intervals, restored primary scores or biological equivalence.'
    (HERE/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    with (HERE/'comparison.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['current_pA','native_pulse_count','paper_mean_Hz','paper_low_Hz','paper_high_Hz','native_minus_paper_low','native_minus_paper_high','visible_mean_difference','whole_recording_count'])
        for r in result['rows']:w.writerow([r['current_pA'],r['model_count_1s'],r['paper_mean_Hz'],*r['paper_mean_interval_Hz'],*r['residual_interval_Hz'],r['visible_mean_residual_Hz'],r['whole_recording_count']])
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(9,5.8),layout='constrained');rs=result['rows'];visible=[r for r in rs if r['paper_mean_Hz'] is not None]
    ax.errorbar([r['current_pA'] for r in visible],[r['paper_mean_Hz'] for r in visible],yerr=[[r['paper_mean_Hz']-r['paper_mean_interval_Hz'][0] for r in visible],[r['paper_mean_interval_Hz'][1]-r['paper_mean_Hz'] for r in visible]],fmt='o-',color='#175fc7',capsize=4,label='Paper control means + reading bounds')
    ax.vlines(100,0,1.2,color='#175fc7',linewidth=3,label='100 pA conditional interval; mean unknown')
    ax.plot([r['current_pA'] for r in rs],[r['model_count_1s'] for r in rs],'s-',color='#bf5527',label='Existing GPU one-second pulse counts')
    ax.set(xlabel='Added current above holding bias (pA)',ylabel='One-second pulse count / spikes per second',title='Post-hoc descriptive comparison: original numerical gate failed',ylim=(-.5,25));ax.set_xticks(range(100,1001,100));ax.grid(alpha=.2);ax.legend(fontsize=9)
    fig.text(.025,-.02,'Figure-reading intervals are not confidence intervals. Paper SEM missing; no simulated biological variance.',fontsize=8)
    fig.savefig(HERE/'comparison.png',dpi=180,bbox_inches='tight');plt.close(fig)
    lines=['# Post-hoc biological comparison', '', '**Explicitly authorized exploratory interpretation after the original numerical gate failed.** This does not reopen the gated primary analysis or establish biological validation. Original report, model, target and thresholds remain unchanged.','', '| Current (pA) | Native pulse count | Frozen paper mean (Hz) | Paper reading interval (Hz) | Native minus paper (Hz) | Whole-recording count |','|---:|---:|---:|---:|---:|---:|']
    for r in rs:
        mean='unidentified' if r['paper_mean_Hz'] is None else f"{r['paper_mean_Hz']:.3f}"
        lines.append(f"| {r['current_pA']} | {r['model_count_1s']:g} | {mean} | [{r['paper_mean_interval_Hz'][0]:.3f}, {r['paper_mean_interval_Hz'][1]:.3f}] | [{r['residual_interval_Hz'][0]:+.3f}, {r['residual_interval_Hz'][1]:+.3f}] | {r['whole_recording_count']} |")
    b=result['exploratory_all_ten_conditional_bounds']
    lines+=['',f"The existing native count exceeds every frozen control-reading interval. Conditional ten-current RMSE is {b['RMSE_bounds_Hz'][0]:.4f}–{b['RMSE_bounds_Hz'][1]:.4f} spikes/s, signed mean difference +{b['signed_mean_error_bounds_Hz'][0]:.4f}–{b['signed_mean_error_bounds_Hz'][1]:.4f}, and maximum absolute difference {b['max_absolute_error_bounds_Hz'][0]:.4f}–{b['max_absolute_error_bounds_Hz'][1]:.4f}. These bounds propagate figure-reading/occlusion uncertainty, not population uncertainty. There is no ten-point estimate because the 100 pA mean remains unidentified.",'','![Exploratory counts comparison](comparison.png)','', 'Descriptively the frozen model fires more at low current and remains above the control mean at high current: greater somatic excitability under this assay. The largest visible difference is around 400 pA (11 versus 1.801 spikes/s). At 1000 pA it is 23 versus 16.821. This is a mismatch of an individual fitted deterministic neuron with a population mean curve, not evidence that every experimental cell disagrees or that Hippocampome generally fails. Counts were stable across all three native timesteps, useful limited engineering evidence; failed timing/recovery-state gates still prevent a validated biological interpretation.','', 'Whole-recording counts include one postpulse event at 500 and 800 pA: 14 versus 13 pulse events, and 20 versus 19. The author code searches the entire imported row, but its imported span is unknown. Either window changes those comparisons; neither is assumed to be the biological truth. No 6 ms exclusion or pulse-endpoint ambiguity changes the existing counts.','', 'The original conditional 100 pA [0,1.2] interval is preserved. A later [0,0.4] geometric bound is source-only sensitivity, not substituted here. Figure SEM endpoints remain missing. The supplemental 17.16 ± 0.6439 Hz statistic is mean per-cell maximum firing, not automatically the 1000 pA mean.','', 'The target comprises 92 NON-PILO control cells from 48 mice, with control medications, slice/age/sex/strain conditions described in the frozen protocol. One fitted deterministic cell has no biological variance or SEM. The model was fitted to earlier evidence; differences in preparation and the model’s uncalibrated temperature dependence are unresolved, and no temperature compensation is introduced. No population p-values, equivalence margin, parameter fitting or current fitting is used. This comparison concerns intrinsic somatic firing counts only, not CA2 synapses, circuits or the paper’s seizure/network conclusions.']
    (HERE/'report.md').write_text('\n'.join(lines)+'\n')
if __name__=='__main__':main()
