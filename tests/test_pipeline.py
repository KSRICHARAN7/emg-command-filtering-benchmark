import sys
import unittest
from dataclasses import replace
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from emg_pipeline import (Bout, Block, Recording, find_bouts, partition,
    endpoints, feature_matrix, make_frames, fit_training_scaler, hold_outputs,
    occupancy, confirm_stable, event_inventory, repetition_roles, samples)
from controllers import Persistence, replay

class PipelineChecks(unittest.TestCase):
    def test_midpoint_odd_rest_is_neither_shared_nor_omitted(self):
        cells, blocks = partition(20,[Bout(1,1,2,5),Bout(2,2,10,15)],{1:'train',2:'evaluation'})
        self.assertEqual([(c.start,c.end) for c in cells],[(0,7),(7,20)])
        owner=np.zeros(20,int)
        for b in blocks:owner[b.start:b.end]+=1
        np.testing.assert_array_equal(owner,np.ones(20,int))

    def test_same_role_cells_merge_but_omitted_roles_do_not(self):
        bs=[Bout(1,i,10+30*i,20+30*i) for i in (1,2,3,4)]
        cells,blocks=partition(180,bs,{1:'train',2:'evaluation',3:'train',4:'train'})
        self.assertEqual([b.role for b in blocks],['train','evaluation','train'])
        self.assertEqual(blocks[-1].cell_indices,(2,3))
        self.assertEqual([b.index for b in blocks],[0,1,2])

    def test_rest_repetition_values_do_not_create_active_bouts(self):
        y=np.array([0,0,1,1,0,0,0,2,2,0]);r=np.array([6,1,1,1,2,3,2,2,2,0])
        self.assertEqual(find_bouts(y,r),[Bout(1,1,2,4),Bout(2,2,7,9)])

    def test_global_endpoint_grid_and_pure_windows(self):
        b=Block(0,17,103,'train',(0,));ee=endpoints(b,30,5)
        self.assertEqual(ee.tolist(),list(range(50,104,5)))
        self.assertTrue(np.all(ee-30>=17));self.assertTrue(np.all(ee<=103))
        self.assertEqual(endpoints(Block(0,0,10,'train',(0,)),30,5).size,0)

    def test_hand_features_order_and_integer_overflow(self):
        x=np.array([[-3,2],[1,2],[-1,2],[3,2]],dtype=np.int8)
        np.testing.assert_allclose(feature_matrix(x,np.array([4]),4)[0],[2,np.sqrt(5),10/3,2,2,0])
        f=feature_matrix(np.array([[-128],[127]],dtype=np.int8),np.array([2]),2)
        np.testing.assert_allclose(f,[[127.5,np.sqrt((128**2+127**2)/2),255]])

    def test_chunking_matches_independent_window_reference(self):
        x=np.random.default_rng(17).normal(size=(71,3));ee=np.arange(10,72,5);expected=[]
        for e in ee:
            w=x[e-10:e];row=[]
            for c in range(3):
                v=w[:,c];row.extend([sum(abs(v))/10,np.sqrt(sum(v*v)/10),sum(abs(np.diff(v)))/9])
            expected.append(row)
        np.testing.assert_allclose(feature_matrix(x,ee,10,1),expected,rtol=1e-14,atol=1e-14)
        np.testing.assert_array_equal(feature_matrix(x,ee,10,3),feature_matrix(x,ee,10,100))

    def test_future_and_left_context_mutations_leave_features_unchanged(self):
        x=np.arange(200,dtype=float).reshape(100,2);ee=np.array([40,45,50])
        expected=feature_matrix(x,ee,20);changed=x.copy();changed[50:]=1e7;changed[:20]=-1e7
        np.testing.assert_array_equal(feature_matrix(changed,ee,20),expected)

    def test_label_is_last_observed_sample_not_endpoint(self):
        x=np.ones((50,2));y=np.zeros(50,int);y[30:]=1
        f=make_frames(Recording(1,200,x,y,np.ones(50,int),y),[Block(0,0,50,'train',(0,))],'train')
        self.assertEqual(f.ends[0],30);self.assertEqual(f.labels[0],0)
        self.assertEqual(f.labels[1],1);self.assertEqual(f.times_seconds[0],.15)

    def test_scaler_is_training_only_with_population_variance_and_constant_scale(self):
        y=np.zeros(100,int);x=np.column_stack([np.arange(100,dtype=float),np.ones(100)])
        rec=Recording(1,200,x,y,y,y)
        blocks=[Block(0,0,50,'train',(0,)),Block(1,50,100,'selection',(1,))]
        train=make_frames(rec,blocks,'train');selected=make_frames(rec,blocks,'selection')
        f=fit_training_scaler(train)
        np.testing.assert_allclose(f.scaler.mean_,np.mean(train.features,axis=0))
        np.testing.assert_allclose(f.scaler.var_,np.var(train.features,axis=0))
        self.assertEqual(f.scaler.scale_[-1],1)
        before=f.scaler.mean_.copy();f.transform(selected);np.testing.assert_array_equal(f.scaler.mean_,before)
        with self.assertRaises(ValueError):fit_training_scaler(selected)
        with self.assertRaises(ValueError):f.transform(replace(selected,subject=2))
        with self.assertRaises(ValueError):f.transform(replace(selected,window_samples=20))

    def test_output_hold_starts_at_endpoint_and_resets_at_gap(self):
        a=Block(0,0,12,'selection',(0,));b=Block(1,20,32,'selection',(1,))
        self.assertEqual(hold_outputs(a,np.array([5,10,12]),np.array([1,2,3])).tolist(),[0]*5+[1]*5+[2]*2)
        self.assertEqual(hold_outputs(b,np.array([25,30]),np.array([0,1])).tolist(),[0]*10+[1]*2)
        p=Persistence(activation=2,release=2,switch=2)
        self.assertEqual(replay(p,[1,1]),[0,1]);self.assertEqual(replay(p,[2]),[0])

    def test_occupancy_is_raw_overlap_with_common_warmup(self):
        b=Block(0,0,100,'selection',(0,));y=np.zeros(100,int);y[53:57]=1
        held=hold_outputs(b,np.array([50,55,60]),np.array([1,0,0]))
        self.assertEqual(occupancy(y,held,b,200),{'scored_samples':50,'warmup_excluded_samples':50,'rest_samples':46,'nonrest_output_during_rest_samples':3})
        self.assertEqual(occupancy(np.zeros(10),np.zeros(10),Block(0,0,10,'x',(0,)),200)['scored_samples'],0)

    def test_stability_is_not_backdated_or_carried_across_gap(self):
        ee=np.arange(0,46,5);p=np.array([0,0,1,1,1,1,1,0,0,0])
        self.assertEqual(confirm_stable(ee,p,1,10,45,20,5),30)
        self.assertIsNone(confirm_stable(ee,p,1,10,30,20,5))
        self.assertEqual(confirm_stable(ee,np.ones(len(ee)),1,11,46,20,5),35)
        self.assertIsNone(confirm_stable(ee,np.zeros(len(ee)),1,10,46,20,5))
        with self.assertRaises(ValueError):confirm_stable(np.array([0,5,30]),np.ones(3),1,0,40,10,5)

    def test_annotation_only_event_eligibility_reasons(self):
        p={'common_warmup_exclusion_ms':250,'eligibility':{'active_duration_min_ms':1000,'pre_onset_rest_min_ms':200,'post_offset_rest_min_ms':500}}
        cells,blocks=partition(900,[Bout(1,1,100,400),Bout(2,2,430,800)],{1:'selection',2:'selection'})
        events=event_inventory(cells,blocks,200,p)
        self.assertFalse(events[0]['eligible']);self.assertIn('following_rest_under_500ms_in_block',events[0]['exclusion_reasons'])
        self.assertIn('preceding_rest_under_200ms_in_block',events[1]['exclusion_reasons'])
        cells,blocks=partition(600,[Bout(1,1,100,400)],{1:'selection'})
        self.assertTrue(event_inventory(cells,blocks,200,p)[0]['eligible'])

    def test_role_maps_invalid_windows_and_timestamps(self):
        p={'development_subjects':[1,2],'confirmatory_subjects':[3],'decoder_train_repetitions':[1,3,4],'development_selection_repetitions':[2,5,6],'confirmatory_evaluation_repetitions':[2,5],'confirmatory_unused_repetitions':[6]}
        self.assertEqual(repetition_roles(1,p)[6],'selection');self.assertEqual(repetition_roles(3,p)[6],'unused')
        with self.assertRaises(ValueError):repetition_roles(11,p)
        with self.assertRaises(ValueError):samples(23,200)
        with self.assertRaises(ValueError):feature_matrix(np.ones((5,2)),np.array([4]),6)
        with self.assertRaises(ValueError):hold_outputs(Block(0,0,5,'x',(0,)),np.array([2.5]),np.array([1]))

    def test_frame_builder_rejects_overlapping_roles_and_bad_bouts(self):
        y=np.zeros(100,int);r=Recording(1,200,np.ones((100,2)),y,y,y)
        with self.assertRaises(ValueError):
            make_frames(r,[Block(0,0,60,'train',(0,)),Block(1,50,100,'evaluation',(1,))],'train')
        with self.assertRaises(ValueError):partition(100,[Bout(1,1,30,20)],{1:'train'})

if __name__=='__main__':unittest.main()
