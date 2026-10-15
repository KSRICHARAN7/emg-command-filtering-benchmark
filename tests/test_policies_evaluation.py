import sys,unittest
from pathlib import Path
from copy import deepcopy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from policies import Policy,rest_calibration
from evaluation import summarize_streams,select,runs
from emg_pipeline import Recording,Bout,Cell,Block,event_inventory,load_protocol,Frames
ROOT=Path(__file__).resolve().parents[1]

class PolicyEvaluationChecks(unittest.TestCase):
    def setUp(self):self.p=load_protocol(ROOT)

    def test_confidence_strict_boundary_and_raw(self):
        p=Policy('confidence_rejection',{'threshold':.7})
        self.assertEqual([p.step(3,x) for x in [.7,.70001,.69]],[0,3,0])
        self.assertEqual(Policy('raw',{}).step(0,.9),0)

    def test_dcir_raw_changes_reset_even_rejected_and_block_reset(self):
        p=Policy('DCIR',{'minimum':.2,'maximum':.8,'tau_ms':100})
        self.assertEqual(p.step(1,.7),0)
        self.assertEqual(p.step(1,.7),1)
        self.assertEqual(p.step(2,.7),0)
        self.assertEqual(p.step(1,.7),0)
        p.reset();self.assertEqual(p.step(1,.8),0)
        self.assertEqual(p.step(1,.8),1)

    def test_mav_nth_lock_includes_zero_ties_and_threshold_reset(self):
        p=Policy('MAV_onset_locking',{'rest_sd_multiplier':2,'initial_votes':3},rest_mean=1,rest_sd=.5)
        self.assertEqual([p.step(x,1,3) for x in [0,2,0,4]],[0,2,0,0])
        self.assertEqual(p.step(5,1,2),0)
        self.assertEqual(p.step(5,1,3),5)
        q=Policy('MAV_onset_locking',{'rest_sd_multiplier':1,'initial_votes':2})
        self.assertEqual([q.step(x,1,1) for x in [1,2,1]],[1,2,2])
        q.reset();self.assertEqual(q.step(1,1,1),1)

    def test_symmetric_diagonal_and_activation_switch_rule(self):
        raw=[1,1,2,1,2,2,0,0,0,3,3]
        for n in [1,2,3,5,7,9]:
            s=Policy('symmetric',{'n':n});a=Policy('asymmetric',{'activation':n,'release':n,'switch_rule':'activation'})
            self.assertEqual([s.step(x) for x in raw],[a.step(x) for x in raw])
        a=Policy('asymmetric',{'activation':2,'release':1,'switch_rule':'activation'})
        self.assertEqual([a.step(x) for x in [1,1,2,2,0]],[0,1,1,2,0])

    def test_majority_available_history_and_tie_retention(self):
        p=Policy('majority',{'n':3})
        self.assertEqual([p.step(x) for x in [1,2,2,1]],[1,1,2,2])
        p.reset();self.assertEqual(p.step(3),3)

    def test_all_policies_prefix_causality(self):
        rng=np.random.default_rng(50);raw=rng.integers(0,18,100);conf=rng.random(100);mav=rng.random(100)
        for family,grid in self.p['controller_grids'].items():
            for params in grid:
                full=Policy(family,params,rest_mean=.2,rest_sd=.1)
                a=[full.step(r,c,m) for r,c,m in zip(raw,conf,mav)]
                prefix=Policy(family,params,rest_mean=.2,rest_sd=.1)
                b=[prefix.step(r,c,m) for r,c,m in zip(raw[:51],conf[:51],mav[:51])]
                self.assertEqual(a[:51],b)

    def synthetic(self):
        y=np.zeros(600,int);y[100:400]=1
        r=Recording(1,200,np.zeros((600,16)),y,np.zeros(600,int),y.copy())
        cell=Cell(0,0,600,'selection',Bout(1,2,100,400));block=Block(0,0,600,'selection',(0,))
        ev=event_inventory([cell],[block],200,self.p)
        ends=np.arange(30,601,5);bid=np.zeros(len(ends),int)
        return r,block,ev,ends,bid

    def test_raw_time_overlap_onset_offset_and_reactivation(self):
        r,b,ev,ee,ids=self.synthetic()
        pred=np.where((ee>=100)&(ee<400),1,0)
        # A wrong-label rest episode is one episode, despite switching class.
        pred[(ee>=450)&(ee<465)]=2;pred[(ee>=465)&(ee<475)]=3
        m,e=summarize_streams(r,[b],ee,ids,pred,ev,self.p)
        self.assertEqual(m['rest_samples'],250)
        self.assertEqual(m['rest_nonzero_samples'],25)
        self.assertEqual(m['rest_exposure'],.1)
        self.assertEqual(m['rest_episodes'],1)
        self.assertEqual(m['longest_rest_episode_ms'],125)
        self.assertEqual(m['rest_episodes_ge_100ms'],1)
        self.assertEqual(m['onset_success'],1)
        self.assertEqual(e[0]['stable_onset_delay_ms'],100)
        self.assertEqual(e[0]['stable_offset_delay_ms'],100)
        self.assertEqual(m['offset_compliance'],1)
        self.assertEqual(m['conditional_mean_first_zero_delay_ms'],0)
        self.assertEqual(m['active_command_coverage'],1)
        self.assertEqual(m['rest_reactivations_after_confirmed_rest_first500ms'],1)

    def test_always_rest_is_not_feasible_and_release_is_flagged(self):
        r,b,ev,ee,ids=self.synthetic()
        m,e=summarize_streams(r,[b],ee,ids,np.zeros(len(ee),int),ev,self.p)
        self.assertEqual(m['onset_success'],0);self.assertEqual(m['offset_compliance'],1)
        self.assertEqual(m['active_command_coverage'],0)
        self.assertEqual(m['already_inactive_before_offset'],1)
        self.assertEqual(m['conditional_active_preoffset_events'],0)
        self.assertIsNone(m['conditional_mean_first_zero_delay_ms'])
        self.assertEqual(m['capped_onset_delay_ms'],1000)

    def test_rest_boundary_clip_and_no_release_search_cutoff_at500ms(self):
        r,b,ev,ee,ids=self.synthetic()
        pred=np.ones(len(ee),int);pred[ee>=530]=0
        m,e=summarize_streams(r,[b],ee,ids,pred,ev,self.p)
        self.assertEqual(m['rest_boundary_clipped_episodes'],1)
        self.assertEqual(e[0]['first_zero_delay_ms'],650)
        self.assertEqual(e[0]['stable_offset_delay_ms'],750)
        self.assertEqual(m['conditional_nonreleases'],0)
        self.assertEqual(m['conditional_late_releases'],1)

    def test_selector_per_person_constraints_shortfalls_and_ties(self):
        def candidate(params,values):
            return {'params':params,'people':[{'metrics':{'onset_success':o,'offset_compliance':f,'active_command_coverage':c,'rest_exposure':x,'false_activation_episodes_per_rest_minute':1,'capped_onset_delay_ms':100},'events':[]} for o,f,c,x in values]}
        bad=candidate({'n':1},[(1,1,1,0),(.8,1,1,0)])
        good=candidate({'n':3},[(.9,.9,.8,.1)]*2)
        self.assertEqual(select([bad,good],self.p)['params'],{'n':3})
        self.assertEqual(select([bad],self.p)['status'],'INFEASIBLE_DESCRIPTIVE_ONLY')
        worse=candidate({'n':5},[(.7,1,1,0)]*2)
        self.assertEqual(select([worse,bad],self.p)['params'],{'n':1})
        tie=deepcopy(good);tie['params']={'n':2}
        self.assertEqual(select([good,tie],self.p)['params'],{'n':2})
        import json
        good['people'][0]['events']=[{'stable_onset_delay_ms':250,'stable_offset_delay_ms':150}]
        good['people'][1]['events']=good['people'][0]['events']
        budget=select([good],self.p,250,150)
        self.assertEqual(budget['status'],'FEASIBLE')
        json.dumps(budget,allow_nan=False)

if __name__=='__main__':unittest.main()
