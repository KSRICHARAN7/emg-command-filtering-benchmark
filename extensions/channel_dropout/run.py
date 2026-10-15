"""Exploratory missing-channel stress test; never overwrites original results."""
from pathlib import Path
from dataclasses import replace
import argparse,datetime,hashlib,importlib.metadata,json,sys
import numpy as np
from threadpoolctl import threadpool_limits
R=Path(__file__).resolve().parents[2];E=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'src'))
from emg_pipeline import load_protocol,load_recording,find_bouts,partition,repetition_roles,make_frames,event_inventory
from decoder import fit_decoder
from final_analysis import replay_final,evaluate_final
METRICS=['rest_exposure','onset_success','offset_compliance','active_command_coverage','interior_correct_fraction','interior_wrong_active_fraction']
def dump(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def conditions():
 return [('intact',[])]+[(f'missing_{i+1:02d}',[i]) for i in range(16)]+[('missing_01_to_08',list(range(8))),('missing_09_to_16',list(range(8,16))),('missing_all',list(range(16)))]
def impute(frames,means,channels):
 if frames.role!='evaluation':raise ValueError('Only evaluation frames may be perturbed')
 if frames.features.shape[1]!=48 or np.shape(means)!=(48,) or not np.isfinite(means).all():raise ValueError('Expected finite 16-channel training means')
 if len(channels)!=len(set(channels)) or any(type(i) is not int or i<0 or i>=16 for i in channels):raise ValueError('Invalid channel mask')
 columns=[3*i+j for i in channels for j in range(3)];x=frames.features.copy();x[:,columns]=means[columns]
 return replace(frames,features=x)
def bootstrap_loss(loss):
 loss=np.asarray(loss,float);assert loss.shape==(8,);rng=np.random.default_rng(5015);draws=loss[rng.integers(0,8,(10000,8))].mean(axis=1)
 return {'participants':8,'mean_loss_correct_pp':float(loss.mean()),'bootstrap_95_percentile_interval_pp':np.percentile(draws,[2.5,97.5]).tolist(),'participant_losses_pp':loss.tolist(),'draws':10000,'seed':5015,'status':'EXPLORATORY_DESCRIPTIVE_ALREADY_EXPOSED_DB5'}
def main(a):
 p=load_protocol(R);data=Path(a.data_root).resolve();out=Path(a.output).resolve()
 if out.exists():raise FileExistsError('Use a new output directory')
 freeze=json.loads((E/'PLAN_FREEZE.json').read_text())
 for name,h in freeze['files_sha256'].items():
  if digest(R/name)!=h:raise ValueError('Extension plan/code changed after lock: '+name)
 if digest(data/p['source_inventory'])!=digest(R/p['source_inventory']):raise ValueError('Source inventory differs')
 locks=json.loads((R/'config/locked_settings.json').read_text());assert locks['db5']['symmetric']['params']=={'n':1};ap=locks['db5']['asymmetric']['params'];assert ap['activation']==1 and ap['release']==2
 specs=[('raw','raw',{}),('asymmetric','asymmetric',ap)];out.mkdir(parents=True)
 manifest={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'plan_freeze_sha256':digest(E/'PLAN_FREEZE.json'),'plan_git_commit':a.plan_commit,'original_outcomes_exposed':True,'extension_analysis_previously_run':False,'dataset':'DB5','participants':list(range(3,11)),'condition_count':20,'controller_count':2,'versions':{k:importlib.metadata.version(k) for k in ['numpy','scipy','scikit-learn','threadpoolctl']},'core_sha256':{str(f.relative_to(R)):digest(f) for f in sorted((R/'src').glob('*.py'))},'source_archive_sha256':{},'historical_trace_comparisons':[]};dump(out/'RUN_MANIFEST.json',manifest)
 rows=[];withheld=[]
 with threadpool_limits(limits=1):
  for subject in range(3,11):
   rec=load_recording(data,subject,p);cells,blocks=partition(len(rec.emg),find_bouts(rec.truth,rec.repetitions),repetition_roles(subject,p))
   train=make_frames(rec,blocks,'train',150,25);f=make_frames(rec,blocks,'evaluation',150,25);events=event_inventory(cells,blocks,rec.fs,p);model=fit_decoder(train,p);means=model.normalizer.scaler.mean_.copy();base_den=None
   old=np.load(Path(a.baseline_predictions)/f'S{subject}_150ms.npz') if a.baseline_predictions else None
   if old is not None:assert np.array_equal(old['endpoints'],f.ends) and np.array_equal(old['block_ids'],f.block_ids)
   for condition,mask in conditions():
    q=impute(f,means,mask);prob=model.probabilities(q);raw=model.model.classes_[prob.argmax(axis=1)]
    if condition=='missing_all':assert np.allclose(prob,prob[0],rtol=0,atol=1e-12)
    if condition=='intact' and old is not None:assert np.array_equal(raw,old['raw'])
    for name,family,params in specs:
     pred=replay_final(family,params,q,blocks,raw,prob.max(axis=1),q.features[:,0::3].mean(axis=1),(0.,0.),p['hop_ms']);m,ev=evaluate_final(rec,blocks,q,pred,events,p)
     den={k:m[k] for k in ['eligible_events','scored_samples','rest_samples','interior_samples']}
     if base_den is None:base_den=den
     assert den==base_den and m['eligible_events']==34
     if condition=='intact' and old is not None:assert np.array_equal(pred,old['selected_'+name])
     rows.append({'subject':subject,'condition':condition,'masked_channels_1_based':[i+1 for i in mask],'controller':name,**den,'metrics':{k:m[k] for k in METRICS},'joint_success':bool(m['onset_success']>=.9 and m['offset_compliance']>=.9 and m['active_command_coverage']>=.8)})
   if old is not None:manifest['historical_trace_comparisons'].append({'subject':subject,'endpoints_exact':True,'raw_exact':True,'asymmetric_exact':True});old.close()
   inv=json.loads((R/p['source_inventory']).read_text());manifest['source_archive_sha256'][str(subject)]=next(x['sha256'] for x in inv if x['subject']==subject)
   dump(out/'participant_metrics.json',rows);print(f'DB5 S{subject}: 20 conditions x 2 controllers; 34 matched events',flush=True)
 original=json.loads((R/'results/db5/method_summary.json').read_text());summary=[];lookup={(r['subject'],r['condition'],r['controller']):r for r in rows}
 for condition,mask in conditions():
  for name,_,_ in specs:
   rr=[r for r in rows if r['condition']==condition and r['controller']==name];base=[lookup[r['subject'],'intact',name] for r in rr]
   avg={k:float(np.mean([r['metrics'][k] for r in rr])) for k in METRICS}
   if condition=='intact':
    expected=next(x for x in original if x['name']=='selected_'+name)['equal_participant_means']
    for k in METRICS:assert np.isclose(avg[k],expected[k],rtol=1e-9,atol=1e-10),(name,k,avg[k],expected[k])
   summary.append({'condition':condition,'masked_channels_1_based':[i+1 for i in mask],'controller':name,'participants':8,'joint_successes':sum(r['joint_success'] for r in rr),'means':avg,'delta_from_intact_pp':{k:float(np.mean([100*(r['metrics'][k]-b['metrics'][k]) for r,b in zip(rr,base)])) for k in METRICS}})
 primary={}
 for name,_,_ in specs:
  loss=[100*(lookup[s,'intact',name]['metrics']['interior_correct_fraction']-np.mean([lookup[s,f'missing_{i:02d}',name]['metrics']['interior_correct_fraction'] for i in range(1,17)])) for s in range(3,11)];primary[name]=bootstrap_loss(loss)
 dump(out/'condition_summary.json',summary);dump(out/'primary_single_channel_loss.json',primary);manifest['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();dump(out/'RUN_MANIFEST.json',manifest)
 dump(out/'VALIDATION.json',{'status':'PASS','participant_condition_controller_evaluations':len(rows),'matched_events_per_evaluation':34,'intact_summary_values_matching_release':12,'all_channel_posteriors_constant':True,'all_scoring_denominators_preserved':True,'historical_trace_checks':len(manifest['historical_trace_comparisons']),'plan_freeze_sha256':manifest['plan_freeze_sha256']})
 print(json.dumps(primary,indent=2),flush=True)
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data-root',default=str(R));parser.add_argument('--output',required=True);parser.add_argument('--baseline-predictions');parser.add_argument('--plan-commit',required=True);main(parser.parse_args())
