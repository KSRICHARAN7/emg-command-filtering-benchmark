"""Frozen personalized LDA baseline; no controller selection or final-data access."""
from dataclasses import dataclass
import numpy as np
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.metrics import confusion_matrix
from emg_pipeline import Frames, TrainingScaler, fit_training_scaler


@dataclass
class Decoder:
    normalizer: TrainingScaler
    model: LinearDiscriminantAnalysis

    def probabilities(self, frames: Frames) -> np.ndarray:
        p = self.model.predict_proba(self.normalizer.transform(frames))
        if (not np.isfinite(p).all() or np.any(p < 0)
                or not np.allclose(p.sum(axis=1), 1, rtol=0, atol=1e-12)):
            raise ValueError('Invalid posterior probabilities')
        return p

    def predict(self, frames: Frames) -> np.ndarray:
        return self.model.classes_[np.argmax(self.probabilities(frames), axis=1)]


def fit_decoder(training: Frames, protocol: dict) -> Decoder:
    if training.role != 'train':
        raise ValueError('Decoder fitting requires training frames')
    expected = np.asarray(protocol['class_labels'])
    if not np.array_equal(expected, np.arange(18)):
        raise ValueError('This implementation requires frozen DB5 labels 0–17')
    if (training.features.ndim != 2 or training.features.shape[1] != 48
            or training.labels.shape != (len(training.features),)
            or not np.isfinite(training.features).all()
            or not np.issubdtype(training.labels.dtype, np.integer)
            or not np.array_equal(np.unique(training.labels), expected)):
        raise ValueError('Finite 48-feature training matrix and all 18 labels required')
    settings = protocol['decoder']
    if settings != {'class':'LinearDiscriminantAnalysis','solver':'lsqr',
                    'shrinkage':'auto','priors':'uniform over18 classes'}:
        raise ValueError('Unexpected decoder settings; protocol amendment required')
    scaler = fit_training_scaler(training)
    model = LinearDiscriminantAnalysis(solver='lsqr', shrinkage='auto',
                                      priors=np.full(18, 1/18))
    model.fit(scaler.transform(training), training.labels)
    if not np.array_equal(model.classes_, expected):
        raise ValueError('Decoder class order mismatch')
    return Decoder(scaler, model)


def diagnostic_counts(truth, predictions, labels=tuple(range(18))) -> dict:
    """Frame diagnostics only; not held-output durations or event feasibility."""
    y, pred = np.asarray(truth), np.asarray(predictions)
    if (y.ndim != 1 or pred.shape != y.shape or not len(y)
            or not np.isin(y, labels).all() or not np.isin(pred, labels).all()):
        raise ValueError('Nonempty aligned labels required')
    cm = confusion_matrix(y, pred, labels=labels)
    support, predicted = cm.sum(axis=1), cm.sum(axis=0)
    tp = np.diag(cm)
    recall = np.divide(tp, support, out=np.zeros(len(labels), float), where=support!=0)
    f1 = np.divide(2*tp, support+predicted, out=np.zeros(len(labels), float), where=(support+predicted)!=0)
    active = y!=0; rest = ~active
    return {'frames':len(y), 'accuracy':float(np.mean(y==pred)),
            'macro_f1_18':float(np.mean(f1)), 'balanced_accuracy_18':float(np.mean(recall)),
            'active_exact_accuracy':float(np.mean(y[active]==pred[active])) if active.any() else None,
            'rest_nonzero_frame_fraction':float(np.mean(pred[rest]!=0)) if rest.any() else None,
            'always_rest_accuracy':float(np.mean(rest)),
            'confusion_matrix_true_rows_predicted_columns':cm.tolist(),
            'per_class':[{'label':int(c),'support':int(n),'predicted':int(q),'recall':float(r),'f1':float(f)}
                         for c,n,q,r,f in zip(labels,support,predicted,recall,f1)]}
