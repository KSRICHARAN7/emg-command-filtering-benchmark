import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from controllers import Persistence,Majority,replay
from metrics import summarize

class Checks(unittest.TestCase):
    def test_asymmetric_activation_release(self):
        self.assertEqual(replay(Persistence(3,1,2),[0,1,1,0,1,1,1,0]),[0,0,0,0,0,0,1,0])
    def test_switch_confirmation(self):
        self.assertEqual(replay(Persistence(1,1,3),[1,2,2,1,2,2,2]),[1,1,1,1,1,1,2])
    def test_causality(self):
        for factory in (lambda:Persistence(2,1,3),lambda:Majority(3)):
            a=replay(factory(),[0,1,1,2,2,2]);b=replay(factory(),[0,1,1,0,0,0])
            self.assertEqual(a[:3],b[:3])
    def test_tie_and_reset(self):
        m=Majority(2);self.assertEqual(replay(m,[1,2,2]),[1,1,2]);m.reset();self.assertEqual(m.step(0),0)
    def test_metric_failures_and_stability(self):
        a=summarize([0,1,1,1,1,0],[0,0,1,1,1,0],25,50,75)
        self.assertEqual(a['stable_onset_delays_ms'],[75]);self.assertEqual(a['onset_budget_success_fraction'],1)
        b=summarize([0,1,1,1,0],[0,0,0,0,0],25,50,250)
        self.assertEqual(b['unreached_onsets'],1);self.assertEqual(b['onset_budget_success_fraction'],0)
    def test_rest_only(self):
        a=summarize([0,0,0,0],[0,1,1,0]);self.assertEqual(a['rest_wrong_time_fraction'],.5)
        self.assertIsNone(a['onset_budget_success_fraction'])

if __name__=='__main__':unittest.main()
