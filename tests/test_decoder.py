import sys,unittest
from pathlib import Path
from dataclasses import replace
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from emg_pipeline import Frames,load_protocol
from decoder import fit_decoder,diagnostic_counts
ROOT=Path(__file__).resolve().parents[1]

class DecoderChecks(unittest.TestCase):
    def setUp(self):
        rng=np.random.default_rng(42); y=np.repeat(np.arange(18),8)
        x=rng.normal(size=(len(y),48));x[np.arange(len(y)),y]+=8
        self.frames=Frames(1,'train',30,5,200,np.arange(len(y)),np.arange(len(y))+30,
                           np.zeros(len(y),int),y,x)
        self.protocol=load_protocol(ROOT)

    def test_training_guards(self):
        for bad in [replace(self.frames,role='selection'),
                    replace(self.frames,labels=np.zeros(len(self.frames.labels),int)),
                    replace(self.frames,features=self.frames.features[:,:47])]:
            with self.assertRaises(ValueError):fit_decoder(bad,self.protocol)

    def test_uniform_priors_class_order_and_probability_mapping(self):
        model=fit_decoder(self.frames,self.protocol)
        np.testing.assert_allclose(model.model.priors_,np.full(18,1/18))
        np.testing.assert_array_equal(model.model.classes_,np.arange(18))
        target=replace(self.frames,role='selection')
        p=model.probabilities(target)
        np.testing.assert_allclose(p.sum(axis=1),1)
        np.testing.assert_array_equal(model.predict(target),
                                      model.model.predict(model.normalizer.transform(target)))
        with self.assertRaises(ValueError):model.predict(replace(target,subject=2))

    def test_prediction_never_uses_heldout_labels_and_does_not_refit(self):
        model=fit_decoder(self.frames,self.protocol)
        mean=model.normalizer.scaler.mean_.copy();coef=model.model.coef_.copy()
        target=replace(self.frames,role='selection')
        a=model.probabilities(target)
        b=model.probabilities(replace(target,labels=np.full(len(target.labels),999)))
        np.testing.assert_array_equal(a,b)
        np.testing.assert_array_equal(mean,model.normalizer.scaler.mean_)
        np.testing.assert_array_equal(coef,model.model.coef_)
        second=fit_decoder(self.frames,self.protocol)
        np.testing.assert_allclose(a,second.probabilities(target),rtol=0,atol=1e-12)

    def test_confusion_diagnostics_hand_example(self):
        d=diagnostic_counts([0,0,1,1],[0,1,1,2],labels=(0,1,2))
        self.assertEqual(d['confusion_matrix_true_rows_predicted_columns'],[[1,1,0],[0,1,1],[0,0,0]])
        self.assertEqual(d['accuracy'],.5)
        self.assertEqual(d['active_exact_accuracy'],.5)
        self.assertEqual(d['rest_nonzero_frame_fraction'],.5)
        self.assertAlmostEqual(d['macro_f1_18'],(2/3+.5)/3)
        with self.assertRaises(ValueError):diagnostic_counts([],[])

if __name__=='__main__':unittest.main()
