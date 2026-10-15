"""Prototype metrics for uniformly sampled decision streams within one real block.
No concatenation across gaps. Outputs are labels at trailing-window endpoints.
Initial active segments are warmup, not annotated rest-to-motion onsets.
"""
import math

def summarize(truth,pred,hop_ms=25,stable_ms=100,budget_ms=250):
    if len(truth)!=len(pred) or not truth:raise ValueError('Equal nonempty streams required')
    if min(hop_ms,stable_ms,budget_ms)<=0:raise ValueError('Positive timing required')
    # Endpoints must span the full requested duration, e.g. 0,25,50 ms.
    stable=math.ceil(stable_ms/hop_ms)+1
    rest=sum(y==0 for y in truth)
    wrong_rest=sum(y==0 and p!=0 for y,p in zip(truth,pred))
    false_events=sum(y==0 and p!=0 and (i==0 or truth[i-1]!=0 or pred[i-1]==0)
                     for i,(y,p) in enumerate(zip(truth,pred)))
    onsets=[i for i in range(1,len(truth)) if truth[i-1]==0 and truth[i]!=0]
    delays=[];fail=0
    for start in onsets:
        label=truth[start];end=start
        while end<len(truth) and truth[end]==label:end+=1
        found=None
        for k in range(start,end-stable+1):
            if all(pred[j]==label for j in range(k,k+stable)):
                # Time is when the full stability interval is available, not its start.
                found=(k+stable-1-start)*hop_ms;break
        if found is None:fail+=1
        else:delays.append(found)
    return {'rest_wrong_time_fraction':wrong_rest/rest if rest else None,
            'false_activations_per_rest_minute':false_events/(rest*hop_ms/60000) if rest else None,
            'onset_count':len(onsets),'unreached_onsets':fail,
            'stable_onset_delays_ms':delays,
            'onset_budget_success_fraction':sum(d<=budget_ms for d in delays)/len(onsets) if onsets else None}
