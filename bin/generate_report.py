#!/usr/bin/env python3
"""Generate a compact reproducible Markdown quantitative-QC report."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def key_values(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return {row[reader.fieldnames[0]]: row[reader.fieldnames[1]] for row in reader}


def table_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def markdown_table(rows: list[dict[str, str]], columns: list[tuple[str, str]]) -> str:
    header = "| " + " | ".join(label for _, label in columns) + " |"
    separator = "|" + "|".join("---" for _ in columns) + "|"
    body = ["| " + " | ".join(row[key] for key, _ in columns) + " |" for row in rows]
    return "\n".join([header, separator, *body])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix-summary", required=True, type=Path)
    parser.add_argument("--quant-dir", required=True, type=Path)
    parser.add_argument("--exploratory-dir", required=True, type=Path)
    parser.add_argument("--design", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--dataset", default="PXD003472")
    parser.add_argument("--versions", default="ProteoWizard 4.0.26282; MSFragger 4.4.1; Philosopher 5.1.0; IonQuant 1.11.20")
    args = parser.parse_args()
    try:
        matrix = key_values(args.matrix_summary.resolve(strict=True))
        quant_dir = args.quant_dir.resolve(strict=True)
        exploratory_dir = args.exploratory_dir.resolve(strict=True)
        quant = key_values(quant_dir / "quant_qc.summary.tsv")
        missing = table_rows(quant_dir / "missingness_by_sample.tsv")
        intensity = table_rows(quant_dir / "intensity_statistics.tsv")
        identification = table_rows(quant_dir / "identification_counts.tsv")
        correlations = table_rows(exploratory_dir / "pairwise_correlations.tsv")
        cv = key_values(exploratory_dir / "protein_cv.summary.tsv")
        pca = table_rows(exploratory_dir / "pca_variance.tsv")
        distances = table_rows(exploratory_dir / "sample_distances.tsv")
        design = table_rows(args.design.resolve(strict=True))
        samples = [row["sample"] for row in design]
        content = f"""# Quantitative QC report

## Scope

Dataset: `{args.dataset}`  
Samples: {', '.join(f'`{sample}`' for sample in samples)}  
Tools: {args.versions}

These three runs are comparable technical repeat measurements used to validate the quantitative workflow. They are one condition and are not independent biological case/control samples. No imputation or differential-abundance testing was performed.

## Identification and LFQ summary

The retained identification path used MSFragger, PeptideProphet, ProteinProphet, and 1% PSM/peptide/protein filtering. IonQuant non-MBR LFQ produced the source protein table used here. Matrix construction began with {matrix['starting_protein_rows']} protein rows, removed {matrix['decoy_rows_removed']} decoys, {matrix['contaminant_rows_removed']} explicit contaminants, and {matrix['unquantified_rows_removed']} all-missing rows, leaving {matrix['final_analytical_rows']} analytical proteins across {matrix['sample_columns']} samples.

{markdown_table(identification, [('sample', 'Sample'), ('filtered_psms', 'Filtered PSMs'), ('unique_peptides', 'Unique peptides'), ('protein_groups_or_proteins', 'Protein groups')])}

## Missingness

Overall analytical-matrix missingness was {float(quant['overall_missingness_percent']):.2f}%. {quant['proteins_quantified_all_samples']} proteins were quantified in every run, {quant['proteins_quantified_exactly_two']} in exactly two runs, and {quant['proteins_quantified_exactly_one']} in exactly one run.

{markdown_table(missing, [('sample', 'Sample'), ('quantified_proteins', 'Quantified proteins'), ('missing_proteins', 'Missing proteins'), ('missingness_percent', 'Missingness (%)')])}

![Protein missingness](../figures/protein_missingness.png)

## Intensity consistency

Statistics use observed log2 MaxLFQ intensities only.

{markdown_table(intensity, [('sample', 'Sample'), ('count', 'N'), ('q1', 'Q1'), ('median', 'Median'), ('q3', 'Q3'), ('mean', 'Mean'), ('standard_deviation', 'SD')])}

![Log2 MaxLFQ distributions](../figures/log2_maxlfq_distributions.png)

## Correlation and variation

Pairwise Pearson and Spearman correlations use only proteins quantified in both samples.

{markdown_table(correlations, [('sample_1', 'Sample 1'), ('sample_2', 'Sample 2'), ('n', 'Pairwise N'), ('pearson_r', 'Pearson r'), ('spearman_rho', 'Spearman rho')])}

CV used sample standard deviation (`ddof=1`) on {cv['eligible_complete_proteins']} proteins quantified in all runs. Median CV was {float(cv['median_cv']):.4f}; Q1-Q3 was {float(cv['q1_cv']):.4f}-{float(cv['q3_cv']):.4f}. Fractions at or below 10%, 20%, and 30% CV were {float(cv['percent_cv_le_0.10']):.1f}%, {float(cv['percent_cv_le_0.20']):.1f}%, and {float(cv['percent_cv_le_0.30']):.1f}%.

![Sample correlation](../figures/sample_correlation_matrix.png)

![Protein CV](../figures/protein_cv_distribution.png)

## PCA and sample distances

PCA treated samples as observations and complete proteins as features. Features were log2 transformed and centered but not variance-scaled. PC1 and PC2 explained {float(pca[0]['explained_variance_fraction']) * 100:.2f}% and {float(pca[1]['explained_variance_fraction']) * 100:.2f}% of the variance. With three samples, rank and interpretation are inherently limited; this plot is technical QC only.

{markdown_table(distances, [('sample_1', 'Sample 1'), ('sample_2', 'Sample 2'), ('euclidean_distance', 'Euclidean distance'), ('complete_proteins', 'Complete proteins')])}

![PCA technical QC](../figures/pca_technical_qc.png)

## Limitations

- D1, D2, and D3 are not used for biological differential inference.
- Missing values were retained; pairwise and complete-case counts are explicit.
- Optional MBR remains deferred because IonQuant 1.11.20 stopped during MBR model fitting on a missing standalone JFree runtime class.
- The reviewed-human PXD024427 search exceeded the safe local 4 GiB JVM heap; this report validates the smaller-proteome yeast route and does not claim human LFQ validation.
- Results are research workflow validation, not clinical evidence.
"""
        if any("/mnt/" in line or ":\\" in line for line in content.splitlines()):
            raise ValueError("report contains an absolute machine path")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
    except (OSError, UnicodeError, ValueError, KeyError, csv.Error) as exc:
        print(f"report-generation error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
