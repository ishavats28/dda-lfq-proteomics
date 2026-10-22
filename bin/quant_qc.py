#!/usr/bin/env python3
"""Calculate descriptive protein-matrix QC and generate restrained figures."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


COLORS = ("#4C78A8", "#59A14F", "#F28E2B")


def write_table(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def short(sample: str) -> str:
    if sample.endswith("_D2"):
        return "D2"
    if sample.endswith("_D3"):
        return "D3"
    return "D1" if "Yeast_HF_60" in sample else sample


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-matrix", required=True, type=Path)
    parser.add_argument("--log2-matrix", required=True, type=Path)
    parser.add_argument("--identification-summary", type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    args = parser.parse_args()
    try:
        raw = pd.read_csv(args.raw_matrix.resolve(strict=True), sep="\t", index_col="protein")
        log2 = pd.read_csv(args.log2_matrix.resolve(strict=True), sep="\t", index_col="protein")
        if list(raw.columns) != list(log2.columns) or not raw.index.equals(log2.index):
            raise ValueError("raw and log2 matrices have different dimensions or labels")
        samples = list(raw.columns)
        total = len(raw)
        observed = raw.notna()
        missing_rows: list[dict[str, object]] = []
        for sample in samples:
            quantified = int(observed[sample].sum())
            missing = total - quantified
            missing_rows.append({
                "sample": sample,
                "quantified_proteins": quantified,
                "missing_proteins": missing,
                "missingness_percent": 100 * missing / total if total else np.nan,
            })
        completeness = observed.sum(axis=1).value_counts().reindex(range(len(samples) + 1), fill_value=0)
        completeness_rows = [
            {"runs_quantified": count, "proteins": int(completeness[count])}
            for count in range(len(samples), 0, -1)
        ]
        values = raw.to_numpy(dtype=float)
        overall_missing = int(np.isnan(values).sum())
        total_cells = values.size
        summary = {
            "analytical_proteins": total,
            "samples": len(samples),
            "overall_missing_values": overall_missing,
            "overall_missingness_percent": 100 * overall_missing / total_cells if total_cells else np.nan,
            "proteins_quantified_all_samples": int(completeness[len(samples)]),
            "proteins_quantified_exactly_two": int(completeness[2]) if len(samples) >= 2 else 0,
            "proteins_quantified_exactly_one": int(completeness[1]),
            "imputation": "none",
        }
        intensity_rows: list[dict[str, object]] = []
        for sample in samples:
            series = log2[sample].dropna()
            intensity_rows.append({
                "sample": sample,
                "count": len(series),
                "minimum": series.min(),
                "q1": series.quantile(0.25),
                "median": series.median(),
                "q3": series.quantile(0.75),
                "maximum": series.max(),
                "mean": series.mean(),
                "standard_deviation": series.std(ddof=1),
            })
        outdir = args.outdir
        figures = outdir / "figures"
        outdir.mkdir(parents=True, exist_ok=True)
        figures.mkdir(exist_ok=True)
        write_table(outdir / "missingness_by_sample.tsv", missing_rows, list(missing_rows[0]))
        write_table(outdir / "completeness_categories.tsv", completeness_rows, list(completeness_rows[0]))
        write_table(outdir / "intensity_statistics.tsv", intensity_rows, list(intensity_rows[0]))
        with (outdir / "quant_qc.summary.tsv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(("field", "value"))
            writer.writerows(summary.items())

        plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
        fig, axes = plt.subplots(1, 2, figsize=(9, 4), constrained_layout=True)
        labels = [short(sample) for sample in samples]
        axes[0].bar(labels, [row["missingness_percent"] for row in missing_rows], color=COLORS[:len(samples)])
        axes[0].set_ylabel("Missing protein values (%)")
        axes[0].set_xlabel("Technical run")
        category_labels = [f"{row['runs_quantified']}/{len(samples)}" for row in completeness_rows]
        axes[1].bar(category_labels, [row["proteins"] for row in completeness_rows], color="#76B7B2")
        axes[1].set_ylabel("Proteins")
        axes[1].set_xlabel("Runs with non-missing intensity")
        fig.savefig(figures / "protein_missingness.png", dpi=180, facecolor="white")
        plt.close(fig)

        fig, axes = plt.subplots(2, 1, figsize=(8, 7), constrained_layout=True)
        for index, sample in enumerate(samples):
            axes[0].hist(log2[sample].dropna(), bins=35, histtype="step", linewidth=1.7,
                         color=COLORS[index], label=short(sample), density=True)
        axes[0].set_xlabel("log2 MaxLFQ intensity")
        axes[0].set_ylabel("Density")
        axes[0].legend(frameon=False)
        axes[1].boxplot([log2[sample].dropna() for sample in samples], tick_labels=labels,
                        patch_artist=True, boxprops={"facecolor": "#B9E3DD"}, medianprops={"color": "#333333"})
        axes[1].set_ylabel("log2 MaxLFQ intensity")
        axes[1].set_xlabel("Technical run")
        fig.savefig(figures / "log2_maxlfq_distributions.png", dpi=180, facecolor="white")
        plt.close(fig)

        if args.identification_summary:
            identification = pd.read_csv(args.identification_summary.resolve(strict=True), sep="\t")
            required = {"sample", "filtered_psms", "unique_peptides", "protein_groups_or_proteins"}
            if not required.issubset(identification.columns):
                raise ValueError("identification summary lacks required count columns")
            identification = identification.set_index("sample").loc[samples]
            identification.reset_index().to_csv(
                outdir / "identification_counts.tsv", sep="\t", index=False, lineterminator="\n"
            )
            fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
            x = np.arange(len(samples))
            width = 0.36
            axes[0].bar(x - width / 2, identification["filtered_psms"], width, label="Filtered PSMs", color="#4C78A8")
            axes[0].bar(x + width / 2, identification["unique_peptides"], width, label="Unique peptides", color="#76B7B2")
            axes[0].set_xticks(x, labels)
            axes[0].set_ylabel("Count")
            axes[0].legend(frameon=False)
            axes[1].bar(x - width / 2, identification["protein_groups_or_proteins"], width,
                        label="Identified", color="#B279A2")
            axes[1].bar(x + width / 2, [int(observed[sample].sum()) for sample in samples], width,
                        label="Quantified", color="#59A14F")
            axes[1].set_xticks(x, labels)
            axes[1].set_ylabel("Proteins / groups")
            axes[1].legend(frameon=False)
            fig.savefig(figures / "identification_quantification_counts.png", dpi=180, facecolor="white")
            plt.close(fig)
    except (OSError, UnicodeError, ValueError, KeyError, pd.errors.ParserError) as exc:
        print(f"quantitative-QC error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
