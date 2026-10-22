# Quantitative QC validation

## Scope and matrix

The genuine three-run non-MBR IonQuant protein table was processed as one technical validation set. No imputation, biological hypothesis testing, or differential-abundance analysis was performed.

| Measure | Result |
|---|---:|
| Source protein rows | 2,859 |
| Explicit decoys removed | 0 |
| Explicit contaminants removed | 20 |
| All-missing rows removed | 934 |
| Final analytical proteins | 1,905 |
| Matrix dimensions | 1,905 proteins × 3 samples |

Positive MaxLFQ values were log2-transformed. Zero and missing values remained missing without a pseudocount. Distinct protein/protein-group identifiers were not silently merged.

## Missingness and distributions

Overall analytical-matrix missingness was 5.93%. There were 1,566 complete proteins, 339 quantified in exactly two runs, and none quantified in exactly one run.

| Run | Quantified | Missing | Missingness | Median log2 MaxLFQ | Mean log2 MaxLFQ | SD |
|---|---:|---:|---:|---:|---:|---:|
| D1 | 1,748 | 157 | 8.24% | 24.692 | 24.992 | 2.166 |
| D2 | 1,818 | 87 | 4.57% | 24.686 | 24.963 | 2.173 |
| D3 | 1,810 | 95 | 4.99% | 24.781 | 25.009 | 2.145 |

## Correlation, CV, and PCA

Pairwise calculations used proteins quantified in both samples without imputation.

| Pair | N | Pearson r | Spearman rho |
|---|---:|---:|---:|
| D1–D2 | 1,661 | 0.9734 | 0.9653 |
| D1–D3 | 1,653 | 0.9735 | 0.9668 |
| D2–D3 | 1,723 | 0.9737 | 0.9641 |

CV used linear MaxLFQ values and sample standard deviation (`ddof=1`) for 1,566 complete proteins. Median CV was 15.22%; Q1 and Q3 were 8.86% and 24.11%. The percentages at or below 10%, 20%, and 30% CV were 29.69%, 65.33%, and 84.42%.

PCA treated samples as observations and complete proteins as features. Values were log2-transformed and protein-centered without variance scaling. PC1 explained 53.18% and PC2 46.82%. With three samples, this is a limited technical-consistency view rather than evidence of biological structure.

Euclidean distances on the centered complete matrix were 18.996 for D1–D2, 18.002 for D1–D3, and 18.334 for D2–D3. A dendrogram was omitted because it added little beyond the correlation, distance, and PCA summaries.

Six compact figures and machine-readable summaries are available under `results/example/`. The differential-design guard rejects this one-condition technical design for biological inference.

## Resources and limits

Peak RSS was 80.4 MB for matrix construction, 130.0 MB for quantitative QC, 148.6 MB for exploratory QC, 11.8 MB for design validation, and 12.0 MB for report generation. The five-process analysis completed in 47.4 seconds and published approximately 1.50 MB of output.

The results demonstrate high run-to-run quantitative consistency in these technical validation runs. They do not establish biological differential abundance, biomarker evidence, or clinical utility.
