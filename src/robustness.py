"""Prespecified robustness helpers. Original raw partitions remain immutable."""
from dataclasses import replace
from collections import Counter,deque
import numpy as np
from scipy.signal import lfilter
from emg_pipeline import find_bouts,event_inventory


def shift_labels(values,offset):
    a=np.asarray(values);out=np.zeros_like(a)
    if offset==0:return a.copy()
    if abs(offset)>=len(a):return out
    if offset>0:out[offset:]=a[:-offset]
    else:out[:offset]=a[-offset:]
    return out


def alternative_events(recording,cells,blocks,truth,repetitions,protocol):
    """Match movement/repetition identities while keeping every primary range."""
    bouts=find_bouts(truth,repetitions)
    lookup={(b.label,b.repetition):b for b in bouts}
    if len(lookup)!=len(bouts) or set(lookup)!={(c.bout.label,c.bout.repetition) for c in cells}:
        raise ValueError('Alternative annotation identity mismatch; do not invent matches')
    cc=[replace(c,bout=lookup[(c.bout.label,c.bout.repetition)]) for c in cells]
    events=event_inventory(cc,blocks,recording.fs,protocol)
    byid={b.index:b for b in blocks}
    for event in events:
        b=byid[event['block']]
        if event['onset_sample']<b.start or event['offset_sample']>b.end:
            event['exclusion_reasons'].append('alternative_bout_crosses_primary_block_boundary');event['eligible']=False
    return replace(recording,truth=np.asarray(truth)),events


def envelope_features(recording,blocks,frames):
    """Causal5Hz envelope, zero state at real block edges, no further scaling."""
    alpha=1-np.exp(-2*np.pi*5/recording.fs)
    mav=np.full(len(frames.ends),np.nan);sd=mav.copy()
    for b in blocks:
        if b.role!=frames.role:continue
        indices=np.flatnonzero(frames.block_ids==b.index)
        raw=recording.emg[b.start:b.end].astype(float)
        env=lfilter([alpha],[1,-(1-alpha)],np.abs(raw),axis=0)
        for j in range(0,len(indices),1024):
            ii=indices[j:j+1024];local=frames.ends[ii]-b.start
            windows=env[local[:,None]+np.arange(-frames.window_samples,0)[None,:]]
            mav[ii]=windows.mean(axis=(1,2));sd[ii]=windows.std(axis=1,ddof=0).mean(axis=1)
    if not np.isfinite(mav).all() or not np.isfinite(sd).all():raise ValueError('Unassigned/nonfinite envelope features')
    return mav,sd


def confirmed_peaks(ends,mav,sd):
    if not (len(ends)==len(mav)==len(sd)):raise ValueError('Aligned peak inputs required')
    for i in range(2,len(ends)):
        if sd[i-1]>sd[i-2] and sd[i-1]>=sd[i] and mav[i-1]>mav[i-2]:
            yield {'peak_index':i-1,'confirmed_index':i,'peak_endpoint':int(ends[i-1]),
                   'confirmation_endpoint':int(ends[i]),'height':float(sd[i-1]),'prepeak_mav':float(mav[i-2])}


def calibrate_otvl(frames,cells,blocks,mav,sd):
    if frames.role!='train':raise ValueError('OTVL calibration requires training frames')
    rest=sd[frames.labels==0]
    if not len(rest):raise ValueError('No fitting rest')
    floor=6*float(np.median(rest));firsts=[]
    for b in blocks:
        if b.role!='train':continue
        ii=np.flatnonzero(frames.block_ids==b.index)
        peaks=list(confirmed_peaks(frames.ends[ii],mav[ii],sd[ii]))
        for cellid in b.cell_indices:
            bout=cells[cellid].bout;mid=bout.start+(bout.end-bout.start)//2
            qualifying=[peak for peak in peaks if bout.start<=peak['peak_endpoint']<mid and peak['height']>floor]
            if qualifying:firsts.append({'label':bout.label,'repetition':bout.repetition,**qualifying[0]})
    return {'available':bool(firsts),'threshold':min(x['height'] for x in firsts) if firsts else None,
            'six_times_training_rest_median_sd':floor,'qualifying_training_bouts':len(firsts),'calibration_peaks':firsts}


class OTVLAdaptation:
    """Fixed exploratory raw-Myo adaptation; never a full published reproduction."""
    def __init__(self,threshold,fs):
        if threshold is None or not np.isfinite(threshold):raise ValueError('Unavailable calibration')
        self.threshold,self.fs=threshold,fs;self.reset()
    def reset(self):
        self.history=deque(maxlen=3);self.votes=deque(maxlen=10)
        self.active=False;self.lock=None;self.peak=None;self.pre=None;self.inhibit_until=0
    def step(self,end,raw,mav,sd):
        self.history.append((int(end),float(mav),float(sd)))
        peak=None
        if len(self.history)==3:
            a,b,c=self.history
            if b[2]>a[2] and b[2]>=c[2] and b[1]>a[1]:peak=(b[2],a[1])
        qualifying=peak is not None and peak[0]>self.threshold
        new=False
        if self.active:
            larger=peak is not None and peak[0]>self.peak
            if mav<self.pre or larger:
                self.active=False;self.lock=None;self.votes.clear()
                if larger and qualifying:new=True
        elif qualifying:new=True
        if new:
            self.active=True;self.peak,self.pre=peak;self.lock=None;self.votes.clear()
            self.inhibit_until=end+int(round(.150*self.fs))
        if not self.active or end<self.inhibit_until:return 0
        if self.lock is not None:return self.lock
        self.votes.append(int(raw));counts=Counter(self.votes)
        tied={k for k,v in counts.items() if v>=8}
        if tied:self.lock=next(v for v in reversed(self.votes) if v in tied);return self.lock
        return int(raw)


def replay_otvl(frames,blocks,raw,mav,sd,calibration):
    if not calibration['available']:return None
    policy=OTVLAdaptation(calibration['threshold'],frames.fs);out=np.full(len(raw),-1,int)
    for b in blocks:
        if b.role!=frames.role:continue
        policy.reset()
        for i in np.flatnonzero(frames.block_ids==b.index):out[i]=policy.step(frames.ends[i],raw[i],mav[i],sd[i])
    if np.any(out<0):raise ValueError('Unassigned OTVL outputs')
    return out
