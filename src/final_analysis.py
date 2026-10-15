"""Final evaluation adapters and participant-level descriptive statistics.

The sealed Step7 metric implementation is reused unchanged. Its internal
'selection' role token is a dispatch label, mapped from final 'evaluation' only.
Raw ranges, labels, events, timing and counts are unchanged by this adapter.
"""
from dataclasses import replace
from itertools import product
import numpy as np
from evaluation import summarize_streams
from policies import Policy


def evaluation_view(blocks,events):
    if any(b.role=='selection' for b in blocks) or any(e['role']=='selection' for e in events):
        raise ValueError('Final adapter rejects development selection roles')
    if not any(b.role=='evaluation' for b in blocks):
        raise ValueError('No final evaluation blocks')
    return ([replace(b,role='selection') if b.role=='evaluation' else b for b in blocks],
            [{**e,'role':'selection'} if e['role']=='evaluation' else dict(e) for e in events])


def replay_final(family,params,frames,blocks,raw,confidence,mav,rest_stats,hop_ms):
    if frames.role!='evaluation':raise ValueError('Evaluation frames required')
    if not (len(frames.ends)==len(raw)==len(confidence)==len(mav)):
        raise ValueError('Aligned decision inputs required')
    policy=Policy(family,params,hop_ms,*rest_stats)
    out=np.full(len(raw),-1,np.int64)
    for b in blocks:
        if b.role!='evaluation':continue
        policy.reset()
        for i in np.flatnonzero(frames.block_ids==b.index):
            out[i]=policy.step(raw[i],confidence[i],mav[i])
    if np.any(out<0):raise ValueError('Unassigned final output')
    return out


def evaluate_final(recording,blocks,frames,predictions,events,protocol):
    if frames.role!='evaluation':raise ValueError('Evaluation frames required')
    bb,ee=evaluation_view(blocks,events)
    return summarize_streams(recording,bb,frames.ends,frames.block_ids,predictions,ee,protocol)


def paired_statistics(differences,draws=10000,seed=20261015):
    d=np.asarray(differences,float)
    if d.ndim!=1 or not len(d) or len(d)>20 or not np.isfinite(d).all():
        raise ValueError('Finite nonempty participant differences required')
    if draws<1:raise ValueError('Positive bootstrap draw count required')
    n=len(d);observed=float(d.mean())
    rng=np.random.default_rng(seed)
    means=d[rng.integers(0,n,size=(draws,n))].mean(axis=1)
    low,high=np.percentile(means,[2.5,97.5],method='linear')
    signs=np.array(list(product([-1,1],repeat=n)),dtype=float)
    permuted=(signs*d).mean(axis=1)
    p=float(np.mean(np.abs(permuted)>=abs(observed)-1e-12))
    return {'participant_differences_pp':d.tolist(),'participants':n,
            'mean_difference_pp':observed,'bootstrap_95_percentile_interval_pp':[float(low),float(high)],
            'bootstrap_draws':draws,'bootstrap_seed':seed,'exact_two_sided_signflip_p':p,
            'sign_assignments':len(signs),'inference_status':'DESCRIPTIVE_ONLY_DEVELOPMENT_FEASIBILITY_FAILED'}


def holm_adjust(p_values):
    p=np.asarray(p_values,float)
    if p.ndim!=1 or not len(p) or not np.isfinite(p).all() or np.any((p<0)|(p>1)):
        raise ValueError('Valid nonempty p values required')
    order=np.argsort(p,kind='stable');adjusted=np.empty(len(p));running=0.
    for rank,i in enumerate(order):
        running=max(running,float((len(p)-rank)*p[i]));adjusted[i]=min(1.,running)
    return adjusted.tolist()
