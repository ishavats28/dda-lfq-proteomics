# Scientific validation overview

## Infrastructure and synthetic integration

The Nextflow DSL2 workflow has deterministic contracts for sample sheets, mzML, FASTA, quantification manifests, and experimental designs. Tests cover malformed inputs, duplicate identifiers, absent tools, resource preflight, empty outputs, and downstream blocking after failure.

A synthetic MSFragger fixture recovered the known peptide `ACDEFGHILMNPQRSTK` with all 32 theoretical fragment ions represented. This verifies search integration but is intentionally not used for statistical FDR claims.

## Human resource-boundary evaluation

One genuine PXD024427 human DDA mzML and a reviewed-human target-decoy database were validated. Both the normal 7–50-aa and constrained 7–35-aa searches reached MSFragger's memory guard before spectrum scoring under the safe 4 GiB Java-heap ceiling. This documents a local workstation memory boundary, not a scientific failure in MSFragger or the pipeline.

## Complete yeast identification and FDR validation

The full path completed on `QExactiveHF_D1__500ng_60min.raw` from PXD003472:

ProteoWizard → mzML QC → MSFragger 4.4.1 → PeptideProphet → ProteinProphet → Philosopher 1% PSM/peptide/protein FDR.

| D1 result | Count |
|---|---:|
| Raw PSMs | 24,657 |
| Filtered PSMs | 14,663 |
| Unique peptides | 11,112 |
| Proteins/protein groups | 2,189 |

See [identification-validation.md](identification-validation.md).

## Three-run LFQ validation

IonQuant 1.11.20 quantified three comparable PXD003472 technical runs with normalization, MaxLFQ, and MBR disabled for the primary analysis.

| Combined result | Count |
|---|---:|
| Ions | 20,148 |
| Peptides | 16,451 |
| Protein rows | 2,859 |
| Proteins with non-zero MaxLFQ | 1,912 |
| Proteins quantified in all runs | 1,682 |

See [lfq-validation.md](lfq-validation.md).

## Quantitative QC

After explicit contaminant removal and all-missing-row removal, the analytical matrix contained 1,905 proteins. Overall missingness was 5.93%, 1,566 proteins were complete across all runs, pairwise Pearson correlations were approximately 0.973, and median complete-case protein CV was 15.22%.

D1, D2, and D3 are technical validation runs, not independent biological groups. See [quantitative-qc-validation.md](quantitative-qc-validation.md).

## Known limitation

Optional IonQuant MBR reached feature extraction and model fitting but stopped because the tested standalone runtime lacked the required JFree class. No unofficial dependency workaround was introduced. The successful non-MBR LFQ result remains the primary validated path.
