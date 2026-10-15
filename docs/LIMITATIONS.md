# Limitations and unresolved work

1. This is offline replay of public intact-limb EMG. No amputee, clinical, user-benefit, closed-loop, real actuator or safety validation was performed.
2. Personalized training uses repetitions 1/3/4 and evaluation uses 2/5. Some training data occur later in the recording than evaluation data. Causal processing is preserved within a replay stream; prospective train-before-test deployment is not established.
3. Refined dataset labels are retrospective annotations. They are neither measured intention nor direct physical actuator events. Annotation shifts and stimulus-label checks show sensitivity; they do not identify true intention timing.
4. The primary DB5 development cohort contains only two people and final cohort eight. The DB2 development/final counts are eight/32. No participant is dropped, but precision and selection stability remain limited.
5. Every development family was infeasible. Fallbacks are explicitly descriptive. Group means, favorable rest exposure, or small descriptive p-values cannot establish constrained superiority.
6. Canonical movement mapping permits the specified replication, but native devices, rates and channels differ. Dataset IDs do not establish that biological participants are independent across datasets. DB2 transported and reselected comparisons share final people.
7. Coverage is any nonzero command during eligible active interiors, including wrong commands. Correct/wrong/zero fractions are separate. Already inactive offsets can count as compliant under the frozen rule; conditional release diagnostics remain essential.
8. Labels partition recordings into owned blocks; history resets at real gaps. Warmup excludes the first 250 ms per block from duration scores. These explicit bookkeeping decisions affect the estimand and differ from continuous unscripted use.
9. Candidate grids and simple LDA pipeline are finite. Logistic regression is a prespecified sensitivity, not a newly optimized rescue model. Feasibility failure applies to these tested methods/settings.
10. The OTVL-inspired adaptation was implemented after primary outcome exposure and is exploratory. It is not a reproduction or validation of the full published system. See calibration details and low-coverage results in Step9/T08.
11. Bootstrap intervals resample participants with a fixed seed and 10,000 draws. DB5 exact sign-flip tests are descriptive after feasibility failure; Holm correction covers the five frozen secondary comparisons only. No new DB2 p-value procedure was introduced.
12. Host timing is finite sampled computation, not end-to-end latency or a hard realtime guarantee. Saved profiles do not measure electrode acquisition, communication or mechanical actuation.
13. Dated freezes are internal records, not a public preregistration. Both datasets' final outcomes are now exposed; reruns must retain that fact. Step10 is post-hoc evidence organization only.
14. E01/E02 use transparent, outcome-based selection for illustration. They are not randomly sampled, representative examples or additional hypothesis tests. No original waveform is reproduced in these figures.
15. This private package includes models and prediction artifacts. Before Step11 public release, review DB5 CC BY-ND 4.0 terms and derivative-artifact handling, attribution, personal metadata and release licensing. Raw data stay outside the project ZIP.

Required future evidence for broader claims: genuinely prospective calibration, independent biological-cohort checks, participant-in-the-loop tasks with measured intentions, amputee validation where appropriate, and real-device timing/actuation studies. None is claimed complete.
