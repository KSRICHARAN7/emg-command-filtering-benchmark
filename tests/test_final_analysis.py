import unittest,sys
from pathlib import Path
from dataclasses import replace
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from final_analysis import evaluation_view,evaluate_final,replay_final,paired_statistics,holm_adjust
from emg_pipeline import Recording,Bout,Cell,Block,Frames,event_inventory,load_protocol
from evaluation import summarize_streams
ROOT=Path(__file__).resolve().parents[1]

class FinalAnalysisChecks(unittest.TestCase):
    def test_zero_and_constant_differences_exact_enumeration(self):
        z=paired_statistics([0]*8);self.assertEqual(z['exact_two_sided_signflip_p'],1)
        self.assertEqual(z['bootstrap_95_percentile_interval_pp'],[0,0])
        a=paired_statistics([1]*8);self.assertEqual(a['exact_two_sided_signflip_p'],2/256)
        self.assertEqual(a['bootstrap_95_percentile_interval_pp'],[1,1])
        self.assertEqual(a['sign_assignments'],256)

    def test_paired_bootstrap_seed_and_sign_reversal(self):
        d=[-.2,.1,.5,.4,.2,.1,.3,.8]
        a=paired_statistics(d);b=paired_statistics(d);self.assertEqual(a,b)
        c=paired_statistics([-v for v in d])
        self.assertEqual(a['exact_two_sided_signflip_p'],c['exact_two_sided_signflip_p'])
        np.testing.assert_allclose(c['bootstrap_95_percentile_interval_pp'],[-v for v in a['bootstrap_95_percentile_interval_pp'][::-1]])
        for bad in [[],[float('nan')],[[1,2]]]:
            with self.assertRaises(ValueError):paired_statistics(bad)

    def test_holm_hand_example_and_ties(self):
        np.testing.assert_allclose(holm_adjust([.01,.04,.03]),[.03,.06,.06])
        np.testing.assert_allclose(holm_adjust([.02,.02,.9]),[.06,.06,.9])
        with self.assertRaises(ValueError):holm_adjust([1.1])

    def fixture(self):
        p=load_protocol(ROOT);y=np.zeros(600,int);y[100:400]=1
        r=Recording(3,200,np.zeros((600,16)),y,np.zeros(600,int),y.copy())
        cell=Cell(0,0,600,'evaluation',Bout(1,2,100,400));block=Block(0,0,600,'evaluation',(0,))
        ev=event_inventory([cell],[block],200,p);ends=np.arange(30,601,5)
        f=Frames(3,'evaluation',30,5,200,ends-30,ends,np.zeros(len(ends),int),y[ends-1],np.zeros((len(ends),48)))
        return p,r,block,ev,f

    def test_role_adapter_preserves_all_metric_inputs(self):
        p,r,b,ev,f=self.fixture();pred=np.where((f.ends>=100)&(f.ends<400),1,0)
        before=repr((b,ev));bb,ee=evaluation_view([b],ev)
        self.assertEqual(before,repr((b,ev)))
        self.assertEqual((bb[0].start,bb[0].end,bb[0].index),(b.start,b.end,b.index))
        expected=summarize_streams(r,bb,f.ends,f.block_ids,pred,ee,p)
        self.assertEqual(evaluate_final(r,[b],f,pred,ev,p),expected)
        self.assertEqual(expected[0]['onset_success'],1)
        with self.assertRaises(ValueError):evaluation_view(bb,ee)

    def test_final_replay_resets_at_real_blocks_and_rejects_unassigned(self):
        p,r,b,ev,f=self.fixture();raw=np.ones(len(f.ends),int)
        a=replay_final('symmetric',{'n':2},f,[b],raw,np.ones(len(raw)),np.zeros(len(raw)),(0,1),25)
        self.assertEqual(a[0],0);self.assertTrue(np.all(a[1:]==1))
        with self.assertRaises(ValueError):replay_final('raw',{},replace(f,role='train'),[b],raw,np.ones(len(raw)),raw,(0,1),25)
        with self.assertRaises(ValueError):replay_final('raw',{},replace(f,block_ids=np.full(len(raw),8)),[b],raw,np.ones(len(raw)),raw,(0,1),25)

if __name__=='__main__':unittest.main()
