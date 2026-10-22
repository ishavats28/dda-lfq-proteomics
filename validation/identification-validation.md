# Identification and FDR validation

## Validation layers

The identification path was evaluated at three levels: deterministic input contracts, a synthetic MSFragger integration fixture, and a complete real-data yeast analysis. A reviewed-human search was also used to characterize the safe memory boundary of the local workstation.

## Synthetic integration

The one-spectrum synthetic fixture completed through Nextflow and produced a genuine 6,368-byte pepXML with one spectrum-query record. MSFragger recovered `ACDEFGHILMNPQRSTK` from `sp|SYN001|SYNTHETIC_ALPHA` with 32 of 32 theoretical fragment ions. Search time was 3.52 seconds, peak RSS was 377,000 kB, the Java heap was 3 GiB, and two threads were configured.

The fixture verifies orchestration, mzML/FASTA handling, parameter materialization, and output validation. Its single observation is not suitable for PeptideProphet, ProteinProphet, or FDR modelling.

## Human resource-boundary evaluation

The human evaluation used one genuine DDA mzML from ProteomeXchange `PXD024427`:

- file: `20170612_QEP8_JaBA_SA_LT01_V1_LC12_8_2FX2D1mS123fM2_sample11.mzML`;
- size: 1,292,945,910 bytes;
- SHA-256: `a84db12b12dca543135c54d4d8dc8b5a2cdcae30913a9af316fac7e027b9aeadf`;
- spectra: 143,398 total, 14,604 MS1, and 128,794 MS2;
- retention-time range: 0.0012772732–159.99821 minutes;
- precursor information and non-empty peak arrays: present.

Philosopher 5.1.0 generated the reviewed UniProt `UP000005640` human reference database with common contaminants, reverse decoys, and `rev_` prefix. It contained 40,928 records, comprising 20,464 targets and 20,464 decoys, with 22,855,948 amino acids. The FASTA was 27,091,752 bytes with SHA-256 `f75c2fd98a5e8f9e5418bbd4fa1c8532eb1b492bfb2d58d7c88dbd9e1a8f9b21`.

The production search used strict trypsin specificity, two missed cleavages, peptide lengths 7–50, ±20 ppm precursor tolerance, 20 ppm fragment tolerance, fixed carbamidomethyl cysteine, variable methionine oxidation, at most two variable modifications, two threads, and a 4 GiB heap. MSFragger generated 5,057,483 unique and 7,576,801 modified peptides, then stopped at its memory guard with `Insufficient memory!` before spectrum scoring. No pepXML was produced.

A separate constrained-machine profile changed only the maximum peptide length from 50 to 35. It generated 4,632,759 unique and 6,650,423 modified peptides and reached the same memory guard before scoring. The Java heap was not raised beyond 4 GiB, and the database, modifications, missed cleavages, and FDR policy were not weakened.

This is a local hardware boundary for the reviewed-human search on the tested 8 GB-class Windows/WSL2 system. It is not evidence of a scientific failure in MSFragger or the workflow.

## Complete yeast validation

The complete path used the public PXD003472 yeast benchmark run `QExactiveHF_D1__500ng_60min.raw`:

- RAW size: 894,270,674 bytes;
- RAW SHA-256: `1a833ad3aa74b74802eef207d45debed42f0153de029ecbfaab633fb832b09f6`;
- instrument/acquisition: Q Exactive HF, DDA, 500 ng, 60-minute method.

ProteoWizard 4.0.26282 converted the RAW with mzML output and vendor peak picking at MS level 1 and above. The output was 350,370,690 bytes with SHA-256 `0b1fa9d7c139984291af0a7763830603a4e305956978724c08634f5dafb7bf38`. Streaming QC found 44,448 spectra: 6,639 MS1 and 37,809 MS2, with retention times from 0.0033040735 to 80.000989 minutes. All spectra contained non-empty peak arrays and MS2 precursor information was present.

The reviewed UniProt `UP000002311` *Saccharomyces cerevisiae* reference database contained Philosopher contaminants and `rev_` reverse decoys. It comprised 12,368 records: 6,184 targets and 6,184 decoys, including 234 prefix-classified contaminant records. The FASTA contained 5,954,554 amino acids, occupied 7,744,770 bytes, and had SHA-256 `61ddd969e489fe444fe4dc1d2e638ee97692acbef483048b0e4c2f346e65177e`.

The unchanged production search generated 1,364,903 unique and 1,992,003 modified peptides, searched all 37,809 MS2 spectra, and emitted 24,657 raw PSM records. Search time was 57.04 seconds with 2,045,212 kB peak RSS and no swaps.

PeptideProphet completed a non-parametric accurate-mass/ppm model. ProteinProphet completed protein inference. Philosopher filtering used the `rev_` prefix, picked proteins, razor assignment, sequential filtering disabled, and fixed PSM/peptide/protein thresholds of 0.01.

| Result | Count |
|---|---:|
| Raw PSMs | 24,657 |
| Filtered target PSMs | 14,663 |
| Unique peptides | 11,112 |
| Proteins/protein groups | 2,189 |
| Retained decoy PSMs in the report | 0 |

The PXD003472 publication reported approximately 16,078 peptide identifications for its Yeast_HF_60 analysis. That value is contextual only because the search engine, database release, settings, and statistical processing differ. No parameter was tuned to reproduce it.

This validates the complete mzML QC → MSFragger → PeptideProphet → ProteinProphet → 1% Philosopher FDR path on one real DDA run. It does not validate biological differential abundance or clinical use.
