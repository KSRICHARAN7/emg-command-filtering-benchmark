# Reproducing the public release

Python3.12 and exact pins in requirements.txt are the reference environment. Install as described in README.md. Downloads require internet access to Ninapro; published aggregate checks and unit tests require no dataset. Other CPUs/BLAS libraries may change floating-point rounding and timing. The first run records Python package versions.

## No-data verification

```bash
python scripts/verify_release.py
python -m unittest discover -s tests -v
```

These check release SHA256 hashes, nine original frozen dependencies, aggregate arithmetic and51 unit tests. They do not establish that an experiment was independently replicated.

## Acquire exact sources

```bash
python scripts/download_data.py --dataset db5
python scripts/download_data.py --dataset db2
```

DB5 original ZIPs total about201MB; DB2 required native members total6.32GB. Both remain under ignored data/raw/. Already matching files are reused. A failed download is retained as .download-part for inspection; remove that incomplete file only after inspecting the reported error before retrying. Inventory files are never overwritten.

For a small diagnostic, download only DB5 S3 or DB2 S9:

```bash
python scripts/download_data.py --dataset db5 --subjects 3
python scripts/reproduce.py --dataset db5 --subjects 3 --output local_runs/db5_s3
python scripts/download_data.py --dataset db2 --subjects 9
python scripts/reproduce.py --dataset db2 --subjects 9 --output local_runs/db2_s9
```

Partial participant runs do not recalculate cohort inference or claim cohort replication.

## Regenerate final comparisons

```bash
python scripts/reproduce.py --dataset db5 --output local_runs/db5_full
python scripts/reproduce.py --dataset db2 --output local_runs/db2_full
```

Each command refits personal decoders from the verified original source training repetitions, applies the published frozen controller settings, and scores all final participants/events. It writes a manifest before fitting, regenerated participant metrics, summary means and paired descriptive contrasts to a new local directory. Full-cohort means are automatically compared with the archived published values. Existing output directories are refused; use a new directory for each reproduction.

No models/predictions need to be downloaded. This public runner reproduces the14 primary DB5 and19 DB2 final method comparisons; it does not repeat the original development search, runtime measurement,23-case sensitivity execution or exploratory OTVL fitting. Those aggregate records, core algorithms and grids are provided for inspection; the complete private study package retains their execution artifacts. Do not describe the public runner as full re-execution of every exploratory/sensitivity analysis.

All original outcomes were exposed before release. Regeneration is reproduction, not a new untouched test. Development-selected settings come from config/locked_settings.json, which identifies hashes of the original private locks. New public entry points do not alter frozen core modules, participant splits, metrics or settings. The historical lock hashes cannot verify withheld private files; PUBLIC_MANIFEST.json verifies everything actually distributed.

See release_validation/ for the executed pre-publication validation record and full-cohort result comparisons, with no sample-level artifacts included.
