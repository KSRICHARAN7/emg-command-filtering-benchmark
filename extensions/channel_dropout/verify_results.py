"""No-data arithmetic/provenance audit for the published extension tables."""
from pathlib import Path
import hashlib,json
import numpy as np
R=Path(__file__).resolve().parents[2];E=Path(__file__).resolve().parent
rows=json.loads((E/'results/participant_metrics.json').read_text());summary=json.loads((E/'results/condition_summary.json').read_text());primary=json.loads((E/'results/primary_single_channel_loss.json').read_text());manifest=json.loads((E/'results/RUN_MANIFEST.json').read_text())
freeze=json.loads((E/'PLAN_FREEZE.json').read_text())
for name,h in freeze['files_sha256'].items():assert hashlib.sha256((R/name).read_bytes()).hexdigest()==h,name
assert hashlib.sha256((E/'PLAN_FREEZE.json').read_bytes()).hexdigest()==manifest['plan_freeze_sha256']
assert len(rows)==320 and len(summary)==40
assert len({(r['subject'],r['condition'],r['controller']) for r in rows})==320
assert {r['subject'] for r in rows}==set(range(3,11));assert all(r['eligible_events']==34 for r in rows)
for s in range(3,11):
 rr=[r for r in rows if r['subject']==s]
 assert all(len({r[k] for r in rr})==1 for k in ['scored_samples','rest_samples','interior_samples'])
for r in rows:
 m=r['metrics'];assert all(0<=v<=1 for v in m.values());assert np.isclose(m['interior_correct_fraction']+m['interior_wrong_active_fraction'],m['active_command_coverage'])
for g in summary:
 rr=[r for r in rows if (r['condition'],r['controller'])==(g['condition'],g['controller'])];assert len(rr)==8
 for k,v in g['means'].items():assert np.isclose(v,np.mean([r['metrics'][k] for r in rr]),rtol=0,atol=1e-12)
 assert g['joint_successes']==sum(r['joint_success'] for r in rr)
for name in ['raw','asymmetric']:
 losses=[]
 for s in range(3,11):
  base=next(r['metrics']['interior_correct_fraction'] for r in rows if r['subject']==s and r['controller']==name and r['condition']=='intact')
  one=[r['metrics']['interior_correct_fraction'] for r in rows if r['subject']==s and r['controller']==name and len(r['masked_channels_1_based'])==1];assert len(one)==16;losses.append(100*(base-np.mean(one)))
 assert np.allclose(losses,primary[name]['participant_losses_pp'],rtol=0,atol=1e-12)
 rng=np.random.default_rng(5015);boot=np.asarray(losses)[rng.integers(0,8,(10000,8))].mean(axis=1)
 assert np.allclose(np.percentile(boot,[2.5,97.5]),primary[name]['bootstrap_95_percentile_interval_pp'],rtol=0,atol=1e-12)
 assert np.isclose(np.mean(losses),primary[name]['mean_loss_correct_pp'],rtol=0,atol=1e-12)
 allrow=next(r for r in summary if r['condition']=='missing_all' and r['controller']==name)
 assert allrow['means']['active_command_coverage']==0 and allrow['means']['interior_correct_fraction']==0 and allrow['means']['rest_exposure']==0
assert len(manifest['historical_trace_comparisons'])==8
assert all(r['joint_successes']==0 for r in summary)
print('PASS: locked inputs, 320 unique cells, preserved denominators, all 40 summaries, participant-paired bootstrap and all-missing sanity result.')
