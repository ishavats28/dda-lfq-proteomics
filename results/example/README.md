# Example quantitative QC outputs

These compact derived outputs summarize the validated three-run PXD003472 yeast analysis. D1, D2, and D3 are technical validation runs, not independent biological groups.

- `identification_summary.tsv`: filtered identification counts for each run.
- `quantification_summary.tsv`: combined IonQuant non-MBR LFQ summary and checksums.
- `protein_matrix_qc.tsv`: analytical-matrix completeness summary.
- `correlations.tsv`: pairwise-complete Pearson and Spearman correlations.
- `sample_distances.tsv`: Euclidean distances on the centered complete log2 matrix.
- `figures/`: six quantitative-QC figures.
- `report/summary.md`: reproducible compact report with relative figure links.

Raw spectra, sequence databases, search outputs, complete PSM tables, and bulk IonQuant tables are intentionally excluded.
