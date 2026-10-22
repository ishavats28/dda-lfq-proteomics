# Human resource-boundary input

The selected public run is `20170612_QEP8_JaBA_SA_LT01_V1_LC12_8_2FX2D1mS123fM2_sample11.mzML` from ProteomeXchange dataset `PXD024427`. The official FragPipe LFQ tutorial assigns that run to experiment `IDHmut`, bioreplicate 1, and DDA acquisition. The pipeline-local sample identifier is `PXD024427_IDHmut_11`; it does not encode additional participant metadata.

The official tutorial distributes its six converted mzML tutorial files through its linked download collection. PRIDE holds the source PXD024427 submission, while the repository record primarily exposes vendor RAW files. Before transfer, the exact mzML object size and source URL must be resolved from the tutorial collection. `bin/download_preflight.py` enforces that the selected file is no larger than 4 GiB and that free space is at least four times the object size plus 15 GiB. It does not perform a download.

Local files belong under `.local/data/PXD024427/`, including a local sample sheet with these values:

| Field | Value |
|---|---|
| sample | `PXD024427_IDHmut_11` |
| condition | `IDHmut` |
| replicate | `1` |
| data type | `DDA` |
| source accession | `PXD024427` |

The local sample sheet must refer to the downloaded mzML with a relative path. Neither it nor the experimental mzML is a repository fixture.

`assets/human-validation-sample.example.tsv` is an authored template only. It becomes executable only after copying it to the ignored local data area and placing the verified mzML at its referenced relative location.

Real-search execution is gated by WSL `MemTotal >= 5.5 GiB`, `MemAvailable >= 4.25 GiB`, project-filesystem free space of at least 25 GiB, and a verified official MSFragger 4.4.1 JAR. If a gate fails, the scientific branch is not launched.
