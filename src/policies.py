"""Core frozen policies. Inputs are current/past decoder outputs only."""
import math
from collections import Counter
import numpy as np
from controllers import Persistence, Majority


def recent_plurality(history):
    counts=Counter(history);best=max(counts.values())
    return next(x for x in reversed(history) if counts[x]==best)


class Policy:
    def __init__(self,family,params,hop_ms=25,rest_mean=0.,rest_sd=0.):
        self.family,self.params,self.hop_ms=family,params,hop_ms
        self.threshold=rest_mean+params.get('rest_sd_multiplier',0)*rest_sd
        if family=='majority':self.base=Majority(params['n'])
        elif family=='symmetric':self.base=Persistence(params['n'],params['n'],params['n'])
        elif family=='asymmetric':self.base=Persistence(params['activation'],params['release'],params['activation'])
        elif family not in ('raw','confidence_rejection','DCIR','MAV_onset_locking'):
            raise ValueError('Unknown family')
        self.reset()

    def reset(self):
        self.previous_raw=None;self.elapsed=0.;self.buffer=[];self.lock=None
        if hasattr(self,'base'):self.base.reset()

    def step(self,raw,confidence=1.,mav=0.):
        f,p=self.family,self.params
        if f=='raw':return int(raw)
        if f in ('majority','symmetric','asymmetric'):return self.base.step(raw)
        if f=='confidence_rejection':return int(raw) if confidence>p['threshold'] else 0
        if f=='DCIR':
            self.elapsed=0. if self.previous_raw!=raw else self.elapsed+self.hop_ms
            self.previous_raw=raw
            threshold=p['minimum']+(p['maximum']-p['minimum'])*math.exp(-self.elapsed/p['tau_ms'])
            return int(raw) if confidence>threshold else 0
        if mav<=self.threshold:
            self.buffer=[];self.lock=None;return 0
        if self.lock is not None:return self.lock
        self.buffer.append(int(raw))
        if len(self.buffer)>=p['initial_votes']:
            self.lock=recent_plurality(self.buffer);return self.lock
        return int(raw)


def rest_calibration(training):
    if training.role!='train':raise ValueError('MAV calibration requires training role')
    m=np.mean(training.features[:,0::3],axis=1)[training.labels==0]
    if not len(m) or not np.isfinite(m).all():raise ValueError('Missing fitting-rest MAV')
    return float(m.mean()),float(m.std(ddof=0))
