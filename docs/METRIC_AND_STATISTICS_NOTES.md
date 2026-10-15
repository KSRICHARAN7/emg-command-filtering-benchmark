# Metric and statistics notes

- Primary denominator: native sample time labeled rest, after common per-block warmup; numerator: held nonzero command time on those samples. This includes post-offset activity. It is not endpoint-frame error rate or event-count rate.
- Time windows: 150 ms trailing features, 25 ms hop. Models receive training-only standardization; LDA has uniform class priors. Movement labels 1–17 and rest 0. Native-rate processing: DB5 200 Hz, DB2 2000 Hz.
- Eligible events: active duration >=1000 ms, >=200 ms pre-rest and >=500 ms post-rest in the same block, onset after warmup. Final counts: DB5 34/person x8=272; DB2 34/person x32=1088. No excluded final participants/events within this frozen inventory.
- Onset success requires a correct command stable for 100 ms, confirmed by <=250 ms after onset. Stop compliance requires stable rest for 100 ms, confirmed by <=150 ms after offset. Confirmation is not backdated; at 25 ms hop, a 100 ms span requires five endpoints.
- Active interior begins 500 ms after onset and ends at annotated offset; coverage >=80% counts all nonzero commands. The three joint requirements are assessed per person. Already inactive offsets and conditional release diagnostics remain in full event files.
- Summary tables show percentages (column suffix _pct); effects use percentage points (_pp). T08 retains source fractions. Means give each participant equal weight; intervals are paired participant bootstraps, not millions of independent EMG samples.
- DB5 primary exact two-sided sign-flip p=0.0078125 is descriptive after infeasible development. The five frozen secondary contrasts use Holm correction. DB2 has stored bootstrap intervals, with no newly introduced p-value. Sensitivity CIs are not simultaneous confidence bands.
- DB2 dataset contrasts use the same final people and must not be added as independent samples. DB5 and DB2 are described separately; biological independence across sources is unverified.
- Full event and participant diagnostics remain in results/step8 and results/step9. The consolidated tables supplement those records and never replace or overwrite them.
