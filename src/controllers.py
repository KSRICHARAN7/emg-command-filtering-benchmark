"""Generic causal baselines, not reproductions of named published algorithms."""
from collections import Counter, deque

class Persistence:
    def __init__(self, activation=1, release=1, switch=1):
        if any(int(v)!=v or v<1 for v in (activation,release,switch)):
            raise ValueError('Persistence counts must be positive integers')
        self.activation,self.release,self.switch=activation,release,switch
        self.reset()
    def reset(self):
        self.state=0; self.pending=None; self.count=0
    def step(self,label):
        label=int(label)
        if label==self.state:
            self.pending=None; self.count=0
            return self.state
        if label==self.pending:self.count+=1
        else:self.pending=label;self.count=1
        threshold=self.activation if self.state==0 else self.release if label==0 else self.switch
        if self.count>=threshold:
            self.state=label;self.pending=None;self.count=0
        return self.state

class Majority:
    def __init__(self,n=3):
        if int(n)!=n or n<1:raise ValueError('n must be a positive integer')
        self.n=n;self.reset()
    def reset(self):self.history=deque(maxlen=self.n);self.state=0
    def step(self,label):
        self.history.append(int(label));counts=Counter(self.history)
        best=max(counts.values()); tied={k for k,v in counts.items() if v==best}
        self.state=self.state if self.state in tied else next(k for k in reversed(self.history) if k in tied)
        return self.state

def replay(policy,labels):
    policy.reset()
    return [policy.step(x) for x in labels]
