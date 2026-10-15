"""Reproduce primary/native DB2 final comparisons using published locked settings.
New output directory required; never rewrites archived findings or claims
untouched evaluation. No fitted artifact or sample-level export is distributed.
"""
from pathlib import Path
import argparse,datetime,hashlib,importlib.metadata,json,sys
import numpy as np
from threadpoolctl import threadpool_limits
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'))
from emg_pipeline import load_protocol,load_recording,find_bouts,partition,repetition_roles,make_frames,event_inventory
from decoder import fit_decoder
from replication import load_db2,fit_db2,replication_bootstrap
from policies import rest_calibration
from final_analysis import replay_final,evaluate_final,paired_statistics
METRICS=['rest_exposure','onset_success','offset_compliance','active_command_coverage','interior_correct_fraction','interior_wrong_active_fraction']
def dump(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def specs(dataset,lock):
 refs=[('raw',{}),('majority',{'n':9}),('confidence_rejection',{'threshold':.97}),('DCIR',{'minimum':.4,'maximum':.989,'tau_ms':480}),('MAV_onset_locking',{'rest_sd_multiplier':3,'initial_votes':6})]
 groups=[('selected',lock['db5'])] if dataset=='db5' else [('transport',lock['db5']),('reselected',lock['db2'])]
 result=[dict(name=prefix+'_'+family,family=family,params=c['params']) for prefix,choices in groups for family,c in choices.items()]
 result +=[dict(name='fixed_'+f,family=f,params=params) for f,params in refs]
 if dataset=='db5':result +=[dict(name='subset_'+f,family='asymmetric',params=c['params']) for f,c in lock['db5_subfamilies'].items()]
 return result

def main(a):
 from verify_release import verify
 verify();p=load_protocol(R)
 if a.dataset=='db2':p=json.loads((R/'config/DB2_replication_v1.0.json').read_text())
 people=a.subjects or p['confirmatory_subjects']
 if len(set(people))!=len(people) or not set(people)<=set(p['confirmatory_subjects']):raise ValueError('Unique final participant IDs required')
 out=Path(a.output).resolve()
 if out.exists():raise FileExistsError('Use a new output directory; preserve reproduction history')
 out.mkdir(parents=True);lock=json.loads((R/'config/locked_settings.json').read_text());ss=specs(a.dataset,lock)
 dump(out/'RUN_MANIFEST.json',dict(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),dataset=a.dataset,subjects=people,prior_outcomes_exposed=True,new_untouched_test=False,settings_sha256=hashlib.sha256((R/'config/locked_settings.json').read_bytes()).hexdigest(),versions={n:importlib.metadata.version(n) for n in ['numpy','scipy','scikit-learn','threadpoolctl']},output_scope='Locally regenerated participant metrics; no serialized model or waveform export'))
 results=[]
 with threadpool_limits(limits=1):
  for subject in people:
   rec=load_recording(R,subject,p) if a.dataset=='db5' else load_db2(R,subject)
   cells,blocks=partition(len(rec.emg),find_bouts(rec.truth,rec.repetitions),repetition_roles(subject,p))
   train=make_frames(rec,blocks,'train',150,25);f=make_frames(rec,blocks,'evaluation',150,25)
   model=fit_decoder(train,p) if a.dataset=='db5' else fit_db2(train);prob=model.probabilities(f)
   raw=model.model.classes_[prob.argmax(axis=1)];events=event_inventory(cells,blocks,rec.fs,p);cal=rest_calibration(train)
   for spec in ss:
    y=replay_final(spec['family'],spec['params'],f,blocks,raw,prob.max(axis=1),f.features[:,0::3].mean(axis=1),cal,p['hop_ms'])
    m,ev=evaluate_final(rec,blocks,f,y,events,p)
    if m['eligible_events']!=34:raise ValueError('Event denominator changed; no cases dropped')
    results.append(dict(subject=subject,**spec,metrics=m))
   dump(out/'participant_metrics.json',results);print(f'{a.dataset} S{subject}: {len(ss)} methods, 34 eligible events',flush=True)
 summaries=[]
 for spec in ss:
  rr=[v for v in results if v['name']==spec['name']];summaries.append(dict(**spec,participants=len(rr),participants_meeting_all_constraints=sum(v['metrics']['onset_success']>=.9 and v['metrics']['offset_compliance']>=.9 and v['metrics']['active_command_coverage']>=.8 for v in rr),means={k:float(np.mean([v['metrics'][k] for v in rr])) for k in METRICS}))
 dump(out/'method_summary.json',summaries)
 # Compare full-cohort numerical summaries to published values; partial runs are diagnostics.
 compared=0
 if sorted(people)==p['confirmatory_subjects']:
  originals=json.loads((R/f'results/{a.dataset}/method_summary.json').read_text())
  for r in summaries:
   old=next(v for v in originals if v['name']==r['name']);oldmean=old.get('means',old.get('equal_participant_means'))
   for k,v in r['means'].items():
    if not np.isclose(v,oldmean[k],rtol=1e-9,atol=1e-10):raise AssertionError(f'Numerical mismatch: {r["name"]} {k}')
    compared+=1
  contrasts={}
  for prefix in (['selected'] if a.dataset=='db5' else ['transport','reselected']):
   lookup={(v['subject'],v['name']):v['metrics']['rest_exposure'] for v in results};diff=[100*(lookup[s,prefix+'_asymmetric']-lookup[s,prefix+'_symmetric']) for s in people]
   # Preserve historical participant order for seed-exact bootstrap reproduction.
   if people!=sorted(people):diff=[100*(lookup[s,prefix+'_asymmetric']-lookup[s,prefix+'_symmetric']) for s in sorted(people)]
   contrasts[prefix]=paired_statistics(diff) if a.dataset=='db5' else replication_bootstrap(diff)
  dump(out/'paired_contrasts.json',contrasts)
 dump(out/'COMPLETED.json',dict(status='PASS',dataset=a.dataset,participants=len(people),person_methods=len(results),summary_metric_values_matching_published=compared,prior_outcomes_exposed=True))
 print(f'Completed: {out}',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dataset',choices=['db5','db2'],required=True);p.add_argument('--subjects',nargs='+',type=int);p.add_argument('--output',required=True);main(p.parse_args())
