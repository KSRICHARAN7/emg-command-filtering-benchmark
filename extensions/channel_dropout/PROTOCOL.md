# Missing-channel robustness extension: locked evaluation plan

Status: exploratory extension. Original benchmark outcomes were already exposed. This plan is written before executing this extension; it is not public preregistration of the original study and does not create an untouched cohort.

## Question and scope

How does the existing DB5 decoder/controller pipeline change when known missing channels are handled by simple training-mean feature imputation? This is a controlled feature-availability stress test, not a model of every disconnection, noisy electrode, or hardware failure.

Use the original DB5 final IDs 3–10, the same exercise and labels, training repetitions 1/3/4, evaluation repetitions 2/5, 150 ms windows and 25 ms hops. Preserve partitioning, warmup, event eligibility and raw-time scoring. Each person has 34 eligible events. Do not use DB2 in this focused extension.

## Fixed models and interventions

Fit each person's original intact-channel LDA decoder and training-only scaler once using the original protocol. Never refit or recalibrate after an intervention. During evaluation only, replace all three features (MAV, RMS, waveform length) of each masked channel with that person's corresponding training feature means. This is equivalent to standardized zeros in the missing dimensions. It assumes the missing channel is known and imputed; it does not detect failures or zero raw voltage.

Evaluate all 20 conditions without selecting a favorable channel:

1. Intact (no imputation).
2. Each of the 16 single-channel masks, channel numbers 1–16.
3. Channels 1–8 masked.
4. Channels 9–16 masked.
5. All 16 channels masked as an information-removal sanity check.

The eight-channel groups are channel-index groups. Do not infer a physical armband mapping from their index alone.

Replay two fixed controllers: raw commands, and the original selected asymmetric fallback (activation 1, release 2). The original selected symmetric count is 1 and is exactly identical to raw output; do not count it as an independent method. Active-to-active switching uses the activation count. No controller search, threshold changes, added decoder, or post-result tuning is allowed.

## Outcomes and primary descriptive estimand

Retain original definitions for rest exposure, timely stable-correct onset, timely stable-rest confirmation, nonzero active-interior coverage, correct active-interior output, wrong active-interior output, and joint feasibility. Coverage is not accuracy. Stable confirmation remains at the confirming endpoint; active-interior scoring starts 500 ms after onset.

Primary: for each of the 8 people, average the asymmetric controller's correct active-interior fraction over all 16 single-channel masks; subtract this from their intact correct fraction. Report the mean of these 8 losses in percentage points. Positive means less correct output with missing channels. Give a descriptive paired participant-bootstrap percentile 95% interval using 10,000 draws, seed 5015. The channel average is taken before bootstrapping people; do not treat channels or frames as independent participants.

Secondary: the corresponding raw-controller estimate, all condition/controller means and changes from each controller's intact baseline, per-condition joint-success counts, and the range across the 16 single-channel cohort means. These are exploratory descriptions. No significance testing or superiority claim; no multiple-comparison-adjusted discovery claim.

## Required checks and reporting

- Intact cohort metrics for both controllers must match the released six-metric summaries (rtol 1e-9, atol 1e-10).
- If historical private prediction traces are available, verify exact intact raw and replayed commands and endpoint alignment for all 8 people.
- No condition may drop evaluation frames, blocks, scored-time denominators or eligible events.
- The all-channel condition must produce identical decoder posteriors at every evaluation frame for a person.
- Verify input archive hashes using the original inventory; record source, protocol, code and environment provenance.
- Keep original core code, historical freeze, manuscript and headline results unchanged. Publish a separately labeled extension with all 20 conditions, including unfavorable outcomes.
- Distribute code and aggregate metrics only; do not publish source EMG, features, fitted models or sample-level traces.

Limits: 8 existing DB5 people, already-seen recordings, one decoder, two fixed controller outputs, no adaptation, no DB2 extension, no intention measurements, physical hardware or closed-loop users. A lower rest-exposure number can reflect loss of useful commands. This extension cannot establish clinical robustness.
