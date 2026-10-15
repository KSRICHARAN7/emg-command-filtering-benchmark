# Frozen research protocol v1.0

**Start and Stop Delay Constraints in EMG Command Filtering: A Reproducible Replay Benchmark**

Protocol ID: DB5-command-filtering-v1.0  
Frozen: 2026-10-15T16:30:42+00:00  
Status: dated internal analysis-plan freeze, **not public preregistration**. This version supersedes the original draft and Step2 proposals where they differ. No features, trained decoders, controller tuning results or final-performance outcomes were available at freeze. Existing exposure comprises source literature, pilot/schema checks and development-only annotation comparisons recorded in Steps1–3.

## 1. Question, hypothesis and claim limits

Test whether independent activation and release persistence improves rest-command exposure compared with symmetric persistence under prespecified onset, stopping and activity requirements. The primary comparator is symmetric persistence; raw decisions, voting, confidence rejection, DCIR and MAV onset locking are required secondary baselines. Asymmetric filtering is a design hypothesis, not an established novel algorithm.

This is offline replay of a synchronized public EMG release from intact-limb participants. Labels are retrospectively refined annotations, not direct timestamps of user intent. No claim of clinical safety, task usability, amputee benefit, full hardware latency or natural active-to-active switching is licensed by these experiments. Dataset acquisition and labels are described in the Step3 report. The source has no direct active-to-active label transitions in the selected task.

## 2. Fixed dataset, participants and roles

Use all16 DB5 EMG channels from filename E2, canonical exercise B:17 movements and rest0. Preserve local labels0–17. Use archive/member filename participant keys; participant2's internal scalar11 is a documented source alias. E2's internal exercise scalar is1. Never select the task using scalar2. Exact archive bytes are locked by the provider-verified inventory and freeze manifest.

| Role | Participants | Repetitions |
|---|---|---|
| Personalized decoder fitting | Each participant separately | 1,3,4 |
| Global controller selection | Development participants1–2 only | 2,5,6 |
| Final evaluation | Confirmatory participants3–10 only | 2,5 |
| Unused in confirmatory cohort | Participants3–10 | 6 |

Development repetitions2/5 are development data, not final-test evidence. This explicit role clarification replaces the generic draft's undifferentiated repetition list. No development outcome has been measured yet. Confirmatory repetition6 is not a personal tuning or calibration set. Personal decoder fitting on repetitions1/3/4 is allowed and required; this is not calibration-free cross-person decoding.

Do not inspect confirmatory performance until implementations pass checks, all development configurations are selected, and a selection-lock file with hashes is saved in Step7. The public data are already acquired, so this protection is procedural rather than an inaccessible physical test server. Structural QC is permitted; visual error diagnosis, feature selection and threshold changes using final cases are not.

## 3. Raw ranges, rest ownership and causal replay

For each recording, derive active bouts from contiguous nonzero `restimulus` with a constant active `rerepetition`. Preserve original sample indices and order. For adjacent bouts `[a_i,b_i)` and `[a_(i+1),b_(i+1))`, set their cell boundary to `floor((b_i+a_(i+1))/2)`. First cell starts at0; last ends atN. Each cell belongs to its active bout's repetition. The midpoint sample belongs to the later cell under half-open intervals. Do not allocate rest using stored rest `rerepetition` values.

Allocate cells to fitting, selection, evaluation or unused roles before making windows. Merge touching cells of the same role into maximal continuous blocks. Never concatenate separated blocks or borrow samples across omitted/unused roles. Controller, filter and feature history reset to rest at each block boundary. Keep natural rest and controller state between touching same-role cells. Each raw sample has exactly one role; tests must verify disjoint role ranges and nonduplicated rest.

At200 Hz, the primary window contains30 samples (150 ms) and the hop5 samples (25 ms). A window is `x[e-L:e]`, its output timestamp is `e/fs`, and its training target is the label at sample `e-1`. Use file-global end indices divisible by the hop, retaining only windows wholly inside a block. No centered windows, future samples, extra filtering, resampling or EMG amplitude normalization fitted on evaluation data.

Before its first decision the block output is0. Hold each emitted label until the next timestamp or block end. Score output occupancy by overlap with raw truth intervals, not by assuming every window has one homogeneous label. For every window-length analysis, omit the first250 ms of each block from duration denominators. Still generate all available causal decisions during that warmup. Report excluded time. Do not omit extra slow-controller warmup beyond this common rule.

All primary reported delay is nominal annotation-to-output replay time. Separately measure processing runtime; do not call the nominal replay delay hardware latency. If measured update time exceeds25 ms on the named machine, flag inability to sustain this update schedule rather than claiming real-time operation.

## 4. Decoder and feature procedure

Use three fixed features per channel: MAV=`mean(abs(x))`; RMS=`sqrt(mean(x*x))`; mean waveform length=`sum(abs(diff(x)))/(L-1)`. Compute in floating point; output48 features in channel-major order `[MAV,RMS,meanWL]`. These three were the original starter feature set. Zero crossings, slope-sign changes, deep models and feature-set search are excluded from the primary analysis.

Fit StandardScaler on all fitting-role windows of that person, with population variance and scale1 for zero-variance features. Fit shrinkage LDA (`solver=lsqr`, `shrinkage=auto`, uniform priors1/18) on those standardized fitting features. Use all fitting windows without random class subsampling. Save fitted scaler/model and training-range hashes. Each person gets one decoder for each prespecified window length; all controllers receive identical outputs within that analysis. Any missing fitting class or numerical fit failure is a recorded failure; do not silently drop a class or person.

Raw class is the maximum posterior, with smallest numerical label breaking exact ties. Posterior values are operating scores, not assumed calibrated probabilities. No personal calibration map, model hyperparameter tuning, decoder refit or online adaptation uses held-out data. Model fitting is performed in Steps6 onward, not during this freeze.

## 5. Controllers and complete candidate grids

All policies start at0 and are strictly causal. No-motion0 explicitly commands zero velocity in the replay abstraction. Holding an active label continues that command. This is different from holding a servo position or transmitting no new command.

| Family | Frozen candidates | Count |
|---|---|---:|
| Raw | Immediate class | 1 |
| Trailing voting | History lengths1,3,5,7,9,13 | 6 |
| Symmetric persistence | Consecutive count1,2,3,5,7,9 for every change | 6 |
| Asymmetric persistence | Activation and release independently in1,2,3,5,7,9 | 36 |
| Fixed confidence rejection | Threshold0,.4,.5,.6,.7,.8,.9,.95,.97,.99 | 10 |
| DCIR | Minimum.2/.4/.6 × maximum.8/.95/.989 × decay100/250/500 ms, plus reference(.4,.989,480 ms) | 28 |
| MAV onset locking | Rest SD multiplier1/2/3/4 × initial votes1/3/5/6/9 | 20 |

Total:107 core family/configuration combinations; numerical duplicates across different families are retained and identified. Asymmetry contains the symmetric diagonal. Its larger tuning space is disclosed; held-out participants assess whether development gains transfer.

Voting uses the current and up to `n-1` past raw decisions, including0; use available history before the buffer fills. Select the plurality. If tied, retain the current output if it is among tied classes, otherwise choose the most recent tied class.

Persistence counts consecutive raw decisions for a pending different label; a different candidate restarts at1, and agreement with current output clears the pending change. On reaching its count, emit the candidate immediately. Symmetric uses the same count for all transitions. Asymmetric uses activation count for0→active, release count for active→0, and activation count for active→different-active. Independent switch-count tuning is removed because direct annotated switches are absent. Switching behavior can influence errors but supports no direct-switch performance claim.

Confidence rejection emits the raw class if its maximum posterior is strictly greater than the threshold, otherwise0. DCIR sets its threshold to `minimum+(maximum-minimum)*exp(-elapsed_ms/tau_ms)` since the last **raw** decision change. At a raw change, elapsed is0. At block start treat the first raw decision as a change. Accept strictly above threshold, otherwise0. The480 ms reference converts the published30 frames at16 ms into physical time for our25 ms updates; it is a declared timing adaptation, not a reproduction of the source acquisition system.

MAV locking uses the mean MAV across channels, in source amplitude units. Determine a threshold from that person's fitting-rest windows: mean plus the candidate multiplier times population SD. Below or equal to threshold, emit0 and clear the lock and buffer. Above threshold, stream raw outputs while collecting the first`n` above-threshold decisions, then lock to their plurality until activity falls below threshold. On the nth decision, use the locked output. Break ties by most recent tied class. Include raw class0 in the buffer. No evaluation labels enter activity detection or threshold fitting.

Fixed reference runs are raw, MV9, CBR.97, DCIR(.4,.989,480 ms) and MAV locking(multiplier3,votes6). Report them separately from the development-selected family settings; do not substitute an untuned reference for the tuned required comparison.

### Extended OTVL adaptation — exploratory only

Use the shared decoder for isolation, clearly labeled as an OTVL-inspired raw-Myo adaptation, not the published full system. At native samples, form each channel's rectified envelope by a causal one-pole low-pass at5 Hz: `z_j=alpha*abs(x_j)+(1-alpha)*z_(j-1)`, `alpha=1-exp(-2*pi*5/fs)`, initialized at0 per block. At each decision endpoint compute mean envelope MAV `m_i` and mean channel envelope population SD `s_i` over the trailing primary window.

A peak at`i-1` is confirmed only at`i` when `s_(i-1)>s_(i-2)` and `s_(i-1)>=s_i`; require rising MAV at the peak. Training calibration uses fitting-role bouts only. In each bout's first half, retain qualifying peaks above six times the median fitting-rest `s`; use the earliest qualifying peak per bout, then the minimum of these peak heights as the onset threshold. If none exists, mark the adaptation unavailable for that person, rather than invent a fallback or use evaluation data.

In replay, a confirmed qualifying peak above that threshold begins activity at the **confirmation** timestamp. Store peak height and the MAV immediately before the peak. While active, terminate on current MAV below stored pre-peak MAV, or a subsequently confirmed peak above the stored onset peak; the latter may begin a fresh contraction if it satisfies onset criteria. No-motion takes precedence during a150 ms inhibit interval after each detected onset. Then stream raw predictions; lock when at least8 of the last10 post-inhibit predictions agree, allowing locking after8 observations if8 agree. Once locked, retain the class until termination/new onset; ties use most recent. No inference is made that this fixed adaptation matches OTVL's published performance. Detector confirmation and envelope delays remain part of replay timing.

Velocity ramps, glove-derived detectors and any new feature/controller inventions are outside confirmatory v1.0. They require an explicitly exploratory label or a prospective amendment before their evaluation. Published S3/S4/S9/S10 remain conceptual and method references; the existing starter code does not yet implement all policies.

## 6. Common event eligibility and metrics

Derive events from the primary annotation, independently of controller output. Eligible bouts must be at least1,000 ms long, have at least200 ms immediately preceding labeled rest in the same block, start after the common warmup, and have at least500 ms of following labeled rest within the same block. Every method uses the same eligible bouts. Keep all17 classes. List every exclusion with reason and counts by person/class; do not discard difficult outcomes. If a person has no eligible bouts or no scored rest, the relevant endpoint is unavailable and no complete-cohort primary inference is made.

**Stable onset:** beginning at the annotated onset time`a`, find the first run of correct active output lasting at least100 ms. All decision endpoints used for confirmation must be at or after`a` and before the bout ends. The timestamp is the final endpoint needed to span100 ms, not the first endpoint retrospectively backdated. At25 ms hop this needs five equal endpoints. Onset success means confirmation no later than`a+250 ms`. Count all eligible bouts in the denominator; unreached and late events are failures. Report first-correct delay separately, confirmed delay among reached events, and unreached/late fractions. Events already carrying the correct command at`a` are flagged, but still require post-onset confirmation.

**Offset compliance:** use all the same annotation-eligible bouts. Starting at annotated offset`b`, require a run of0 spanning100 ms, confirmed by`b+150 ms`. This is an output-state requirement with a common denominator. If already inactive immediately before`b`, flag that event explicitly; do not portray it as evidence of a quick release. Separately report actual release delays only among bouts whose held output immediately before`b` was nonzero, with their denominator, nonreleases and late releases. These conditional delay summaries are not directly comparable if eligibility fractions differ across controllers. Rest reactivations after confirmation remain errors in rest exposure and are counted separately during the first500 ms.

**Active-command coverage guard:** on all eligible bout interiors `[a+500 ms,b)`, measure the fraction of time output is nonzero. Require at least80% during development selection. This guard stops a policy from passing by briefly activating and then withholding nearly the whole movement. It does not establish correctness; separately report correct-command, wrong-active-class and zero-output fractions over these same interiors, and over full active bouts. The80% requirement is a declared engineering scenario, not an accepted clinical threshold.

**Primary rest exposure:** nonzero held-output duration overlapping annotated rest, divided by scored rest duration, across the complete evaluation-role blocks after common warmup. Use raw-time overlap at5 ms resolution. Do not limit this denominator to eligible bouts or remove post-offset errors. This is an annotation-relative proxy for unintended command exposure, not physical injury risk.

Also report rest episodes per rest minute (contiguous nonzero output intersecting rest; clip at rest boundaries; do not split merely because the wrong active label changes), episodes lasting at least100 ms, longest episode, switches per scored minute, first500 ms reactivations after offset, missed onsets, active zero-output interruptions and runtime. Do not count a transition across an omitted gap. Distinguish boundary episodes already active when scoring begins. Denominators and units must accompany every rate. Never impute a failed delay as zero.

## 7. Development-only configuration selection

For each family, evaluate its entire finite grid on selection-role repetitions of people1–2. Each development person must separately achieve onset success≥.90, offset compliance≥.90 and active-command coverage≥.80. This is a point-estimate feasibility rule, not a statistical guarantee. The budgets and guard are fixed now, before empirical feasibility is known. This replaces Step2's proposal to check feasibility before fixing them because decoder training occurs later in the roadmap. Do not change these goals merely to obtain a feasible result.

Among feasible settings minimize the equal-person mean rest exposure. Break exact ties by equal-person mean false-activation episode rate, then equal-person mean capped confirmed onset delay (unreached=1,000 ms, late values capped at1,000 ms for tie-breaking only), then ascending canonical parameter JSON. Runtime is measured but not a stochastic tie-break.

If no setting meets all requirements, mark the family infeasible. Select a **descriptive-only** representative by minimizing the worst normalized shortfall across people/constraints (`max(0,(target-observed)/target)`), then the mean of those shortfalls, then the same exposure and tie-break rules. If asymmetric or symmetric persistence is infeasible, the feasible-constrained primary hypothesis is not estimable as planned; record this null feasibility result, and label any fallback comparison descriptive. Do not silently call a fallback budget-feasible or relax constraints.

Freeze selected parameters, statuses, grid tables, input hashes and exact software environment in a dated Step7 selection-lock record before final evaluation. They are **not** claimed selected in Step4. Reusing the same final set to alter settings is prohibited.

## 8. Final evaluation and statistical analysis

Evaluate the locked settings on repetitions2/5 of people3–10, after fitting each person's decoder only on1/3/4. Compute metrics per person before aggregation; eight people, not thousands of independent windows, determine the primary sample size. The maximum annotation-eligible final movement count is272; actual eligibility is resolved by the frozen rules in Step5.

Primary estimate: equal-person mean paired difference in rest exposure, asymmetric minus symmetric, in percentage points; negative favors asymmetric. Show every person's paired values and attained onset/compliance/coverage. A development-feasible setting can fail on final people; do not retune. A claim of meeting the goals across the final cohort requires every person to meet all three criteria; otherwise report the exposure contrast and the violations without a universal budget-compliance claim.

Use10,000 paired participant bootstrap draws, seed20261015, for the2.5th/97.5th percentile interval of the mean paired difference. Report its instability with eight participants. For a two-sided primary test enumerate all256 sign assignments of the eight paired differences, and compute the fraction with absolute mean at least the observed absolute mean (tolerance1e-12). This test assumes sign exchangeability under the null; there was no randomized clinical allocation and no causal clinical interpretation is made. Alpha=.05. Report effect, interval and exact p together; significance alone is insufficient.

Five prespecified secondary contrasts compare asymmetric with raw, tuned voting, tuned CBR, tuned DCIR and tuned MAV locking. Use the same participant-level sign-flip procedure and Holm correction across those five. OTVL adaptation, ablations, alternate annotations and sensitivity models are descriptive; no cherry-picked unadjusted superiority claims. If either primary family was development-infeasible, all final fallback contrasts are descriptive and any p-values, if produced for transparency, carry that label.

No power claim is made: N is fixed by available DB5 participants and held-out design. Do not drop a person for poor model accuracy. Missing class, corrupt source, invalid split, fit failure or metric denominator failure must stop the affected primary analysis and be recorded; no post-hoc complete-case primary replacement is allowed. Fix implementation bugs with logged changes and rerun all affected methods. If final outcomes have already been exposed, the rerun is not a new untouched test.

## 9. Robustness and replication commitments

- Windows100/200/250 ms: same features and fixed decoder settings, refit per-person training features and reselect each controller family on development people only. Lock these selections before any corresponding final evaluation. Common warmup remains250 ms.
- Joint budget grid: activation150/250/350/500 ms × offset100/150/250 ms, including primary250/150. Use the same development-only selector and activity guard; report every cell and infeasibility. This is a secondary frontier, not twelve interchangeable primary tests.
- Confirmation50/150 ms: rescore primary locked streams, without changing controllers. Keep the primary delay budgets and disclose resulting infeasibility. No reoptimization for favorable confirmation results.
- Annotation sensitivity: rescore primary streams using `stimulus`, plus complete primary-label stream shifts of−100/−50/+50/+100 ms with rest padding at recording edges. Retain the primary raw partitions and trained decoder; do not move split boundaries. Reapply common eligibility and report coverage changes.
- Activation-only and release-only subfamilies: evaluate the prespecified asymmetric-grid subsets with release=1 or activation=1. Select them on development data and report their paired descriptive contrasts. The diagonal gives the symmetry control; do not call a different grid search a new algorithm.
- Decoder sensitivity: StandardScaler and LogisticRegression(C=1,class_weight=balanced,solver=lbfgs,max_iter=2000), fitted on the same raw training roles. Apply LDA-selected temporal parameters unchanged; classify nonconvergence as a recorded sensitivity failure rather than tune on final people.

DB2 replication is a prospectively specified extension conditional on source-schema verification: canonical B (expected filename E1,17 classes), native12 channels at2,000 Hz, same physical windows/hop and three features, personalized fitting reps1/3/4. Use DB2 people1–8 for development selection reps2/5/6, people9–40 for final reps2/5, and keep their rep6 unused. Primary replication transports the DB5-selected temporal parameters to separately fitted DB2 decoders; a secondary comparison reselects parameters only on DB2 development people. All mappings/repetitions must be verified before fitting; a mismatch requires a dated amendment before affected evaluation. Acquisition is pending; this protocol does not certify files not yet acquired. Do not assume biological independence merely because dataset IDs differ. No zero-shot decoder/device-transfer claim is made.

## 10. Reproducibility and change control

Freeze the human-readable protocol, machine-readable JSON and original archive hashes together in `FREEZE_RECORD_v1.0.json`. Save the dated files to Drive; no public registry identifier exists, so describe this honestly as a dated internal freeze, never as completed public preregistration. A public preregistration remains possible before final testing, with its actual date and exposure history disclosed.

The frozen JSON enumerates107 core candidates. Validate disjoint roles, complete labels and the nested symmetric diagonal. Step5 must verify raw-range separation, causal endpoint alignment, block resets and time-weighted metrics with hand-checkable examples. Step7 must validate confidence/locking implementations, emit the selection-lock file and record runtime/package versions before Step8. Starter-code tests alone do not establish scientific readiness.

Keep this exact v1.0 intact. Changes require a numbered dated amendment stating the reason, affected rules, whether development/final outcomes were known, and new hashes. Protocol text and machine configuration must change together. Earlier drafts remain as history, with clear supersession notices. No manuscript is written by this protocol task; the user writes the manuscript.

## Sources and refresh

Method references: Smith et al.(2011), DOI10.1109/TNSRE.2010.2100828; Farrell(2011), DOI10.1682/jrrd.2011.03.0055; Raghu et al.(2023), DOI10.1109/JBHI.2023.3316599, author copy https://arxiv.org/html/2409.14169v1; Pero et al.(2026), DOI10.1109/TNSRE.2026.3730074, https://iris.santannapisa.it/handle/11382/590616; Zhang et al.(2017), DOI10.3389/fnbot.2017.00051. Data: Pizzolato et al.(2017), DOI10.1371/journal.pone.0186132 and dataset DOI10.5281/zenodo.1000116.

A focused refresh on15 October2026 searched the revised joint-constraint/asymmetric-persistence terms using two search engines and rechecked the nearest temporal-control records. No exact full-protocol duplicate was identified in that bounded refresh. This is not exhaustive novelty clearance. The Step2 audit's conservative benchmark framing remains in force.
