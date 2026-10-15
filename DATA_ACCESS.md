# Data access and attribution

The repository redistributes no waveforms, label arrays, extracted feature arrays, fitted models or sample-level command traces. Public outputs are original code, metadata, participant/aggregate statistics and analytical figures. Data remain subject to their own terms; MIT applies only to original project code/documentation.

## Ninapro DB5

Pizzolato S, Tagliapietra L, Cognolato M, Reggiani M, Müller H, Atzori M. *Ninapro dataset5 (double Myo armband)*, v1 (2017). Dataset DOI: https://doi.org/10.5281/zenodo.1000116. Official instructions: https://ninapro.hevs.ch/instructions/DB5.html.

Paper: Pizzolato et al. *Comparison of six electromyography acquisition setups on hand movement classification tasks*. PLOS ONE12(10):e0186132 (2017). https://doi.org/10.1371/journal.pone.0186132.

The captured dataset metadata identifies CC BY-ND4.0: https://creativecommons.org/licenses/by-nd/4.0/ (legal text: https://creativecommons.org/licenses/by-nd/4.0/legalcode.en). Preserve source credit and notices. The published download script obtains unchanged original archives and verifies recorded SHA256, provider MD5, size and archive CRC. The recorded source notices are in data/DATASET_LICENSE_AND_ATTRIBUTION.md. This release makes no blanket determination about the legal status of fitted models or derived traces; they are withheld.

## Ninapro DB2

Atzori et al. *Electromyographic data for non-invasive naturally-controlled robotic hand prostheses*. Scientific Data1:140053 (2014). https://doi.org/10.1038/sdata.2014.53. Dataset: https://doi.org/10.5061/dryad.1k84r. Instructions: https://ninapro.hevs.ch/instructions/DB2.html.

Captured Dryad metadata specifies CC0-1.0. Retain attribution. Only the unchanged E1 MATLAB members for canonical exerciseB are required; these total about6.32GB across40 people. Range downloads verify recorded member SHA256, size, compressed length, decompression completion and CRC. They do not verify a full-archive provider checksum. If a provider changes layout/content, the script stops rather than selecting another file.

DB5 uses filenameE2, whose internal exercise scalar is1; DB2 uses filenameE1. The historical derived DB2 config retains an unused DB5 filename_exercise field; the DB2 loader explicitly uses verified E1 members. S2 in DB5 has internal subject alias11. Source bytes are never changed to hide these documented differences.

Dataset creators do not endorse this benchmark. Do not upload downloaded data or locally generated artifacts to this repository.
