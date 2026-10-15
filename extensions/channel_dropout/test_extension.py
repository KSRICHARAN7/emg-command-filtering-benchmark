from pathlib import Path
import sys,unittest
from types import SimpleNamespace
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run import impute,conditions,bootstrap_loss
class ExtensionChecks(unittest.TestCase):
 def test_training_mean_only_and_no_input_mutation(self):
  x=np.arange(144,dtype=float).reshape(3,48);original=x.copy();f=SimpleNamespace(role='evaluation',features=x)
  # Use the real frozen Frames dataclass for immutable schema-preserving copies.
  from emg_pipeline import Frames
  f=Frames(3,'evaluation',30,5,200,np.arange(3),np.arange(3),np.zeros(3,int),np.ones(3,int),x)
  m=np.arange(48,dtype=float)*-2;q=impute(f,m,[1,15]);cols=[3,4,5,45,46,47]
  self.assertTrue(np.array_equal(q.features[:,cols],np.broadcast_to(m[cols],(3,6))))
  self.assertTrue(np.array_equal(x,original));self.assertTrue(np.array_equal(q.ends,f.ends));self.assertTrue(np.array_equal(q.features[:,0:3],x[:,0:3]))
  from dataclasses import replace
  with self.assertRaises(ValueError):impute(replace(f,role='train'),m,[1])
  for bad in [[16],[-1],[1,1],[1.5]]:
   with self.assertRaises(ValueError):impute(f,m,bad)
  allq=impute(f,m,list(range(16)));self.assertTrue(np.array_equal(allq.features,np.broadcast_to(m,(3,48))))
 def test_condition_inventory_and_paired_unit(self):
  self.assertEqual(len(conditions()),20);self.assertEqual(len({n for n,_ in conditions()}),20)
  b=bootstrap_loss([2.]*8);self.assertEqual(b['mean_loss_correct_pp'],2.);self.assertEqual(b['bootstrap_95_percentile_interval_pp'],[2.,2.])
if __name__=='__main__':unittest.main()
