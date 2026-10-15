"""Raw-time replay metrics and frozen development selection, no fitting."""
import json
import numpy as np
from emg_pipeline import hold_outputs,confirm_stable,samples


def runs(mask):
    padded=np.r_[False,np.asarray(mask,bool),False]
    edges=np.flatnonzero(padded[1:]!=padded[:-1])
    return list(zip(edges[::2].tolist(),edges[1::2].tolist()))


def summarize_streams(recording,blocks,ends,block_ids,predictions,events,protocol):
    fs=recording.fs;hop=samples(protocol['hop_ms'],fs)
    stable=samples(protocol['stable_duration_ms'],fs);warm=samples(protocol['common_warmup_exclusion_ms'],fs)
    selected=[b for b in blocks if b.role=='selection']
    counts={k:0 for k in ['scored_samples','excluded_warmup_samples','rest_samples','rest_nonzero_samples',
        'rest_episodes','rest_episodes_ge_100ms','rest_boundary_clipped_episodes','longest_rest_episode_samples',
        'switches','active_zero_interruptions','active_zero_boundary_clipped_episodes',
        'interior_samples','interior_correct_samples','interior_wrong_active_samples','interior_zero_samples',
        'full_active_samples','full_active_correct_samples','full_active_wrong_active_samples','full_active_zero_samples']}
    event_results=[]
    for block in selected:
        mask=block_ids==block.index;ee=np.asarray(ends)[mask];pp=np.asarray(predictions)[mask]
        held=hold_outputs(block,ee,pp);truth=recording.truth[block.start:block.end]
        cut=min(warm,len(held));yy=truth[cut:];hh=held[cut:]
        counts['scored_samples']+=len(yy);counts['excluded_warmup_samples']+=cut
        rest=yy==0;badrest=rest&(hh!=0)
        counts['rest_samples']+=int(rest.sum());counts['rest_nonzero_samples']+=int(badrest.sum())
        rr=runs(badrest);counts['rest_episodes']+=len(rr)
        counts['rest_episodes_ge_100ms']+=sum(b-a>=samples(100,fs) for a,b in rr)
        counts['longest_rest_episode_samples']=max([counts['longest_rest_episode_samples']]+[b-a for a,b in rr])
        if rr and rr[0][0]==0 and cut>0 and truth[cut-1]==0 and held[cut-1]!=0:
            counts['rest_boundary_clipped_episodes']+=1
        # Count actual switches at scored sample times, with preceding warmup state.
        counts['switches']+=int(np.sum(held[max(1,cut):]!=held[max(1,cut)-1:-1]))
        rz=runs((yy!=0)&(hh==0));counts['active_zero_interruptions']+=len(rz)
        if rz and rz[0][0]==0 and cut>0 and truth[cut-1]!=0 and held[cut-1]==0:
            counts['active_zero_boundary_clipped_episodes']+=1
        for event in events:
            if event['role']!='selection' or event['block']!=block.index or not event['eligible']:continue
            a,b,label=event['onset_sample'],event['offset_sample'],event['label']
            rest_end=b+event['following_rest_samples']
            next_end=b+samples(500,fs)
            on=confirm_stable(ee,pp,label,a,b,stable,hop)
            off=confirm_stable(ee,pp,0,b,rest_end,stable,hop)
            zero=ee[(ee>=b)&(ee<rest_end)&(pp==0)]
            correct=ee[(ee>=a)&(ee<b)&(pp==label)]
            onset_delay=(on-a)*1000/fs if on is not None else None
            offset_delay=(off-b)*1000/fs if off is not None else None
            pre=held[b-1-block.start]!=0
            # First500ms new rest activations only, after first reaching a confirmed rest state.
            segment=held[b-block.start:next_end-block.start]
            prev=np.r_[held[b-1-block.start],segment[:-1]]
            transitions=np.flatnonzero((segment!=0)&(prev==0))+b
            after_confirmation=int(np.sum(transitions>=off)) if off is not None else 0
            event_results.append({'label':label,'repetition':event['repetition'],'onset_sample':a,'offset_sample':b,
                'first_correct_delay_ms':float((correct[0]-a)*1000/fs) if len(correct) else None,
                'stable_onset_delay_ms':onset_delay,'onset_success':onset_delay is not None and onset_delay<=protocol['onset_budget_ms'],
                'already_correct_before_onset':bool(held[a-1-block.start]==label),
                'first_zero_delay_ms':float((zero[0]-b)*1000/fs) if len(zero) else None,
                'stable_offset_delay_ms':offset_delay,'offset_compliant':offset_delay is not None and offset_delay<=protocol['offset_budget_ms'],
                'active_immediately_before_offset':bool(pre),'already_inactive_before_offset':not bool(pre),
                'rest_reactivations_first500ms':len(transitions),'rest_reactivations_after_confirmed_rest_first500ms':after_confirmation})
            for prefix,left in [('interior',a+samples(protocol['active_coverage_interior_starts_ms_after_onset'],fs)),('full_active',a)]:
                segment=held[left-block.start:b-block.start]
                counts[prefix+'_samples']+=len(segment)
                counts[prefix+'_correct_samples']+=int(np.sum(segment==label))
                counts[prefix+'_wrong_active_samples']+=int(np.sum((segment!=0)&(segment!=label)))
                counts[prefix+'_zero_samples']+=int(np.sum(segment==0))
    n=len(event_results)
    if not n or not counts['rest_samples'] or not counts['interior_samples']:
        raise ValueError('Required metric denominator unavailable')
    delays=[e['stable_onset_delay_ms'] for e in event_results if e['stable_onset_delay_ms'] is not None]
    activeoff=[e for e in event_results if e['active_immediately_before_offset']]
    release=[e['stable_offset_delay_ms'] for e in activeoff if e['stable_offset_delay_ms'] is not None]
    out={**counts,'eligible_events':n,'onset_success':sum(e['onset_success'] for e in event_results)/n,
         'offset_compliance':sum(e['offset_compliant'] for e in event_results)/n,
         'active_command_coverage':1-counts['interior_zero_samples']/counts['interior_samples'],
         'rest_exposure':counts['rest_nonzero_samples']/counts['rest_samples'],
         'false_activation_episodes_per_rest_minute':counts['rest_episodes']/(counts['rest_samples']/fs/60),
         'rest_episodes_ge100ms_per_rest_minute':counts['rest_episodes_ge_100ms']/(counts['rest_samples']/fs/60),
         'longest_rest_episode_ms':counts['longest_rest_episode_samples']*1000/fs,
         'switches_per_scored_minute':counts['switches']/(counts['scored_samples']/fs/60),
         'capped_onset_delay_ms':float(np.mean([min(e['stable_onset_delay_ms'],1000) if e['stable_onset_delay_ms'] is not None else 1000 for e in event_results])),
         'unreached_onsets':n-len(delays),'late_onsets':sum(d>protocol['onset_budget_ms'] for d in delays),
         'mean_reached_onset_delay_ms':float(np.mean(delays)) if delays else None,
         'already_correct_before_onset':sum(e['already_correct_before_onset'] for e in event_results),
         'already_inactive_before_offset':n-len(activeoff),'conditional_active_preoffset_events':len(activeoff),
         'conditional_nonreleases':sum(e['first_zero_delay_ms'] is None for e in activeoff),
         'conditional_no_stable_release':len(activeoff)-len(release),
         'conditional_mean_first_zero_delay_ms':float(np.mean([e['first_zero_delay_ms'] for e in activeoff if e['first_zero_delay_ms'] is not None])) if any(e['first_zero_delay_ms'] is not None for e in activeoff) else None,
         'conditional_late_releases':sum(d>protocol['offset_budget_ms'] for d in release),
         'conditional_mean_reached_stable_release_ms':float(np.mean(release)) if release else None,
         'rest_reactivations_first500ms':sum(e['rest_reactivations_first500ms'] for e in event_results),
         'rest_reactivations_after_confirmed_rest_first500ms':sum(e['rest_reactivations_after_confirmed_rest_first500ms'] for e in event_results)}
    for prefix in ['interior','full_active']:
        for kind in ['correct','wrong_active','zero']:
            out[prefix+'_'+kind+'_fraction']=counts[prefix+'_'+kind+'_samples']/counts[prefix+'_samples']
    return out,event_results


def canonical(params):return json.dumps(params,sort_keys=True,separators=(',',':'))


def select(candidates,protocol,onset_budget=None,offset_budget=None):
    """Candidates contain parameters plus participant metrics/event outcomes."""
    targets=[protocol['minimum_onset_success'],protocol['minimum_offset_compliance'],protocol['minimum_active_command_coverage']]
    ranked=[]
    for c in candidates:
        short=[];objectives=[];rates=[];delays=[]
        for person in c['people']:
            m=person['metrics']
            onset=m['onset_success'];offset=m['offset_compliance']
            if onset_budget is not None:
                onset=np.mean([e['stable_onset_delay_ms'] is not None and e['stable_onset_delay_ms']<=onset_budget for e in person['events']])
            if offset_budget is not None:
                offset=np.mean([e['stable_offset_delay_ms'] is not None and e['stable_offset_delay_ms']<=offset_budget for e in person['events']])
            obs=[onset,offset,m['active_command_coverage']]
            short.extend(max(0,(t-o)/t) for t,o in zip(targets,obs))
            objectives.append(m['rest_exposure']);rates.append(m['false_activation_episodes_per_rest_minute']);delays.append(m['capped_onset_delay_ms'])
        key=(max(short),float(np.mean(short)),float(np.mean(objectives)),float(np.mean(rates)),float(np.mean(delays)),canonical(c['params']))
        ranked.append((key,c))
    if not ranked:raise ValueError('Empty family')
    ranked.sort(key=lambda x:x[0]);key,c=ranked[0]
    return {'params':c['params'],'status':'FEASIBLE' if key[0]==0 else 'INFEASIBLE_DESCRIPTIVE_ONLY',
            'feasible_candidates':int(sum(k[0]==0 for k,_ in ranked)),'candidate_count':len(candidates),
            'worst_normalized_shortfall':float(key[0]),'mean_normalized_shortfall':key[1],
            'mean_rest_exposure':key[2],'mean_episodes_per_rest_minute':key[3],'mean_capped_onset_delay_ms':key[4]}
