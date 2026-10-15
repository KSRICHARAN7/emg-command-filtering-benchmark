"""DB2 native-channel adapter; fixed decoder and participant-only bootstrap."""
from pathlib import Path
import hashlib,json
import numpy as np
from scipy.io import loadmat
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from emg_pipeline import Recording,fit_training_scaler
from decoder import Decoder


def load_db2(root,subject):
    root=Path(root);rows=json.loads((root/'data/replication/DB2_schema_inventory.json').read_text())
    matches=[r for r in rows if r['subject']==subject]
    if len(matches)!=1:raise ValueError('Unique verified DB2 source required')
    row=matches[0];path=root/row['local_path']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=row['member_sha256']:raise ValueError('DB2 source hash mismatch')
    d=loadmat(path,variable_names=['emg','restimulus','rerepetition','stimulus','subject','exercise'])
    x=d['emg'];y=d['restimulus'].ravel().astype(int);rep=d['rerepetition'].ravel().astype(int)
    if x.shape!=(len(y),12) or int(d['subject'].item())!=subject or int(d['exercise'].item())!=1:
        raise ValueError('DB2 source schema changed')
    if not np.isfinite(x).all() or not np.array_equal(np.unique(y),np.arange(18)):raise ValueError('Invalid DB2 signal/classes')
    return Recording(subject,2000,x,y,rep,d['stimulus'].ravel().astype(int),row['source_member'])


def fit_db2(training):
    if (training.role!='train' or training.features.ndim!=2 or training.features.shape[1]!=36
        or not np.array_equal(np.unique(training.labels),np.arange(18)) or training.fs!=2000):
        raise ValueError('Native DB2 training frames with36 features/all18 classes required')
    scaler=fit_training_scaler(training)
    model=LinearDiscriminantAnalysis(solver='lsqr',shrinkage='auto',priors=np.full(18,1/18))
    model.fit(scaler.transform(training),training.labels)
    return Decoder(scaler,model)


def replication_bootstrap(differences,seed=20261015,draws=10000):
    d=np.asarray(differences,float)
    if d.ndim!=1 or not len(d) or not np.isfinite(d).all():raise ValueError('Finite participant differences required')
    rng=np.random.default_rng(seed);means=d[rng.integers(0,len(d),size=(draws,len(d)))].mean(axis=1)
    return {'participants':len(d),'participant_differences_pp':d.tolist(),'mean_difference_pp':float(d.mean()),
            'bootstrap_95_percentile_interval_pp':np.percentile(means,[2.5,97.5],method='linear').tolist(),
            'bootstrap_draws':draws,'seed':seed,'inference_status':'DESCRIPTIVE_REPLICATION',
            'signflip_p':None,'reason_no_signflip_p':'The frozen exact2^8 test is DB5-specific; no new DB2 p-value procedure introduced'}
