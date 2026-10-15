import sys,unittest
from pathlib import Path
from dataclasses import replace
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from robustness import shift_labels,alternative_events,envelope_features,confirmed_peaks,calibrate_otvl,OTVLAdaptation
from emg_pipeline import Recording,Cell,Bout,Block,Frames,load_protocol
ROOT=Path(__file__).resolve().parents[1]

class RobustnessChecks(unittest.TestCase):
    def test_shifts_zero_pad_without_wrap(self):
        np.testing.assert_array_equal(shift_labels([1,2,3,4],1),[0,1,2,3])
        np.testing.assert_array_equal(shift_labels([1,2,3,4],-1),[2,3,4,0])
        np.testing.assert_array_equal(shift_labels([1,2],2),[0,0])

    def test_alternative_annotation_keeps_partition_and_rechecks_eligibility(self):
        p=load_protocol(ROOT);y=np.zeros(600,int);y[100:400]=1;reps=np.zeros(600,int);reps[100:400]=2
        r=Recording(3,200,np.zeros((600,16)),y,reps,y.copy());c=Cell(0,0,600,'evaluation',Bout(1,2,100,400));b=Block(0,0,600,'evaluation',(0,))
        rr,ev=alternative_events(r,[c],[b],shift_labels(y,10),shift_labels(reps,10),p)
        self.assertEqual(ev[0]['onset_sample'],110);self.assertTrue(ev[0]['eligible']);self.assertEqual(b.start,0)
        self.assertEqual(r.truth[100],1);self.assertEqual(rr.truth[100],0)
        with self.assertRaises(ValueError):alternative_events(r,[c],[b],np.zeros_like(y),reps,p)

    def test_envelope_matches_hand_recursion_and_future_mutation(self):
        x=np.arange(60).reshape(30,2)-20;y=np.zeros(30,int)
        r=Recording(1,200,x,y,y,y);b=Block(0,0,30,'train',(0,));ee=np.array([5,10,15,20,25,30]);f=Frames(1,'train',5,5,200,ee-5,ee,np.zeros(6,int),np.zeros(6,int),np.zeros((6,6)))
        m,s=envelope_features(r,[b],f);alpha=1-np.exp(-2*np.pi*5/200);env=np.zeros_like(x,dtype=float);z=np.zeros(2)
        for i,row in enumerate(x):z=alpha*np.abs(row.astype(float))+(1-alpha)*z;env[i]=z
        self.assertAlmostEqual(m[0],env[:5].mean());self.assertAlmostEqual(s[0],env[:5].std(axis=0).mean())
        xx=x.copy();xx[15:]=10000;mm,ss=envelope_features(replace(r,emg=xx),[b],f)
        np.testing.assert_array_equal(m[:3],mm[:3]);np.testing.assert_array_equal(s[:3],ss[:3])

    def test_peak_is_only_available_at_confirmation(self):
        peaks=list(confirmed_peaks([0,5,10],[1,2,2],[1,3,2]))
        self.assertEqual(peaks[0]['peak_endpoint'],5);self.assertEqual(peaks[0]['confirmation_endpoint'],10)
        self.assertEqual(list(confirmed_peaks([0,5],[1,2],[1,3])),[])

    def test_otvl_inhibit_lock_and_reset(self):
        p=OTVLAdaptation(2,200)
        self.assertEqual(p.step(0,1,1,1),0);self.assertEqual(p.step(5,1,2,3),0)
        self.assertEqual(p.step(10,1,2,2),0) # Peak confirmed now; inhibit to40.
        for t in range(15,40,5):self.assertEqual(p.step(t,2,2,2),0)
        for t in range(40,80,5):self.assertEqual(p.step(t,2,2,2),2)
        self.assertEqual(p.step(80,4,2,2),2) # Eight votes lock2.
        self.assertEqual(p.step(85,4,.5,1),0)
        p.reset();self.assertEqual(p.step(90,3,2,2),0)

    def test_otvl_missing_calibration_is_not_fabricated(self):
        ee=np.array([5,10,15]);f=Frames(1,'train',5,5,200,ee-5,ee,np.zeros(3,int),np.zeros(3,int),np.zeros((3,48)))
        b=Block(0,0,20,'train',(0,));c=Cell(0,0,20,'train',Bout(1,1,5,15))
        cal=calibrate_otvl(f,[c],[b],np.ones(3),np.ones(3));self.assertFalse(cal['available']);self.assertIsNone(cal['threshold'])
        with self.assertRaises(ValueError):OTVLAdaptation(None,200)

if __name__=='__main__':unittest.main()
