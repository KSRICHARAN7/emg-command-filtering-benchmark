import unittest,sys
from pathlib import Path
from dataclasses import replace
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from emg_pipeline import Frames,samples
from replication import fit_db2,replication_bootstrap

class ReplicationChecks(unittest.TestCase):
    def frame(self):
        rng=np.random.default_rng(5);y=np.repeat(np.arange(18),8);x=rng.normal(size=(len(y),36))
        return Frames(1,'train',300,50,2000,np.arange(len(y)),np.arange(len(y))+300,np.zeros(len(y),int),y,x)
    def test_native_physical_timing(self):
        self.assertEqual(samples(150,2000),300);self.assertEqual(samples(25,2000),50)
        self.assertEqual(samples(100,2000),200)
    def test_db2_features_priors_and_selection_inference(self):
        f=self.frame();m=fit_db2(f)
        np.testing.assert_allclose(m.model.priors_,np.full(18,1/18))
        self.assertEqual(m.probabilities(replace(f,role='selection')).shape,(144,18))
    def test_db2_refuses_db5_dimensions_or_heldout_fit(self):
        f=self.frame()
        for bad in [replace(f,role='evaluation'),replace(f,fs=200),replace(f,features=np.zeros((144,48)))]:
            with self.assertRaises(ValueError):fit_db2(bad)
    def test_replication_bootstrap_32_participants_not_window_inference(self):
        r=replication_bootstrap([2]*32);self.assertEqual(r['participants'],32)
        self.assertEqual(r['bootstrap_95_percentile_interval_pp'],[2,2]);self.assertIsNone(r['signflip_p'])
    def test_replication_bootstrap_reproducible_and_invalid_guard(self):
        self.assertEqual(replication_bootstrap([1,2,3]),replication_bootstrap([1,2,3]))
        with self.assertRaises(ValueError):replication_bootstrap([float('nan')])

if __name__=='__main__':unittest.main()
