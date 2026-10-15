# Missing-channel robustness: exploratory DB5 extension

**Completed on October 15, 2026. Original benchmark and manuscript unchanged.**

[Locked plan](PROTOCOL.md) · [Pre-execution plan commit](https://github.com/KSRICHARAN7/emg-command-filtering-benchmark/commit/2d08211d65c72dc4c98859004ae71197f66d17d7) · [Validation](results/VALIDATION.json)

## Main finding

With the fixed asymmetric fallback, the mean participant-averaged loss of correct active-interior output across all 16 single-channel masks was **6.355 percentage points** (descriptive paired bootstrap 95% interval **5.328–7.567 pp**; 8 people). The intact mean was 58.098%; the average single-channel mean was 51.743%. All 8 participant-average losses were positive.

The corresponding raw-controller loss was **6.395 pp** [5.385, 7.586]. These close values do not establish equal robustness or superiority between controllers.

## Conditions and outcomes

All percentages below are equal-participant means. “One channel, averaged” first averages all 16 masks within each person; it does not select the worst or best channel.

| Controller | Condition | Correct interior output (%) | Wrong active output (%) | Active coverage (%) | Rest exposure (%) | Joint successes |
|---|---|---:|---:|---:|---:|---:|
| raw | Intact | 57.765 | 35.537 | 93.302 | 7.217 | 0/8 |
| raw | One channel, averaged | 51.370 | 41.249 | 92.619 | 7.953 | 0/8 |
| raw | Channels 1–8 missing | 25.503 | 55.019 | 80.522 | 3.445 | 0/8 |
| raw | Channels 9–16 missing | 27.515 | 59.611 | 87.125 | 18.754 | 0/8 |
| raw | All channels missing | 0.000 | 0.000 | 0.000 | 0.000 | 0/8 |
| asymmetric | Intact | 58.098 | 36.290 | 94.388 | 8.295 | 0/8 |
| asymmetric | One channel, averaged | 51.743 | 42.091 | 93.834 | 9.122 | 0/8 |
| asymmetric | Channels 1–8 missing | 26.151 | 56.913 | 83.064 | 4.078 | 0/8 |
| asymmetric | Channels 9–16 missing | 27.968 | 61.150 | 89.118 | 19.945 | 0/8 |
| asymmetric | All channels missing | 0.000 | 0.000 | 0.000 | 0.000 | 0/8 |

The averaged single-channel row has 0/8 joint successes under every one of its 16 constituent masks. Every one of the 40 condition/controller cells had zero joint successes.

## Why exposure alone is misleading

Imputing all channels makes the decoder issue rest throughout evaluation for all 8 people. Rest exposure becomes 0%, but so do active coverage and correct output. This is information removal, not improved control. Losing channels 1–8 also lowers rest exposure while sharply reducing correct output. A quiet decoder can be a failed decoder.

## Method and provenance

DB5 IDs 3–10; same source archives, original training/evaluation roles, windows, hop, event eligibility, warmup and native-time scorer. Intact decoders are fit once; at evaluation, the missing channel’s three features are replaced by its training means. No refitting or tuning. Raw and the original asymmetric activation-1/release-2 fallback are fixed. Selected symmetric persistence is count 1, identical to raw, so it is not counted twice. Eight-channel groups are index groups; no physical armband attribution is inferred.

There are 20 conditions × 2 controllers × 8 people = **320 evaluations**, each retaining **34 events** and identical scoring denominators. All 12 intact cohort metric values matched the release; archived intact endpoint/raw/asymmetric commands matched exactly for all 8 people. All-channel posteriors were constant within person. The no-data audit independently rechecks aggregate arithmetic and participant-paired bootstrap values.

The plan and runner were committed before extension execution. The original study outcomes were already exposed; this extension is exploratory and is not a fresh untouched test. Only participant aggregates and cohort summaries are released. No EMG, features, fitted models or sample traces are redistributed.

## Reproduce

Install the original repository requirements and acquire DB5 using `scripts/download_data.py`. Then:

```bash
python extensions/channel_dropout/run.py --data-root . --output local_runs/channel_dropout_v1 --plan-commit 2d08211d65c72dc4c98859004ae71197f66d17d7
python extensions/channel_dropout/verify_results.py
python -m unittest discover -s extensions/channel_dropout -p test_extension.py -v
```

The runner refuses an existing output directory and checks locked plan/code/source hashes. `--baseline-predictions` is an optional private historical-trace comparison; no such files are required for public reproduction. The no-data auditor checks the archived published extension results, not a new run.

## Limits

Eight already-seen DB5 people, one decoder and one deterministic imputation strategy. Missing channels are assumed known; raw-voltage dropout, detection errors, drift, adaptation, and hardware behavior are not modeled. No DB2 extension or new cohort was run. The intervals are descriptive; no significance, clinical robustness, or controller-superiority claim is made. Original limitations about annotations, intact limbs and closed-loop generalization continue to apply.
