#!/usr/bin/env python3
"""Run correlation, CV, PCA, and sample-distance technical QC."""

from __future__ import annotations

import argparse
import csv
import itertools
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr


def short(sample: str) -> str:
    if sample.endswith("_D2"):
        return "D2"
    if sample.endswith("_D3"):
        return "D3"
    return "D1" if "Yeast_HF_60" in sample else sample


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-matrix", required=True, type=Path)
    parser.add_argument("--log2-matrix", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    args = parser.parse_args()
    try:
        raw = pd.read_csv(args.raw_matrix.resolve(strict=True), sep="\t", index_col="protein")
        log2 = pd.read_csv(args.log2_matrix.resolve(strict=True), sep="\t", index_col="protein")
        if list(raw.columns) != list(log2.columns) or not raw.index.equals(log2.index):
            raise ValueError("raw and log2 matrices differ")
        samples = list(raw.columns)
        if len(samples) < 3:
            raise ValueError("PCA technical QC requires at least three samples")
        correlations: list[dict[str, object]] = []
        pearson_matrix = pd.DataFrame(np.eye(len(samples)), index=samples, columns=samples)
        for left, right in itertools.combinations(samples, 2):
            pair = log2[[left, right]].dropna()
            if len(pair) < 3:
                raise ValueError(f"insufficient pairwise observations for {left} and {right}")
            pearson = pearsonr(pair[left], pair[right]).statistic
            spearman = spearmanr(pair[left], pair[right]).statistic
            correlations.append({"sample_1": left, "sample_2": right, "n": len(pair),
                                 "pearson_r": pearson, "spearman_rho": spearman})
            pearson_matrix.loc[left, right] = pearson
            pearson_matrix.loc[right, left] = pearson
        complete_raw = raw.dropna()
        complete_log2 = log2.loc[complete_raw.index]
        means = complete_raw.mean(axis=1)
        cv = complete_raw.std(axis=1, ddof=1) / means
        cv = cv.replace([np.inf, -np.inf], np.nan).dropna()
        cv_summary = {
            "eligible_complete_proteins": len(cv),
            "standard_deviation": "sample (ddof=1)",
            "median_cv": cv.median(),
            "q1_cv": cv.quantile(0.25),
            "q3_cv": cv.quantile(0.75),
            "percent_cv_le_0.10": 100 * (cv <= 0.10).mean(),
            "percent_cv_le_0.20": 100 * (cv <= 0.20).mean(),
            "percent_cv_le_0.30": 100 * (cv <= 0.30).mean(),
        }
        x = complete_log2.to_numpy(dtype=float).T
        centered = x - x.mean(axis=0, keepdims=True)
        u, singular, _ = np.linalg.svd(centered, full_matrices=False)
        scores = u * singular
        variance = singular ** 2
        explained = variance / variance.sum()
        pca_rows = [{"sample": sample, "PC1": scores[index, 0], "PC2": scores[index, 1]}
                    for index, sample in enumerate(samples)]
        distance = np.sqrt(((centered[:, None, :] - centered[None, :, :]) ** 2).sum(axis=2))
        distance_rows = [
            {"sample_1": left, "sample_2": right, "euclidean_distance": distance[i, j],
             "complete_proteins": len(complete_log2)}
            for i, left in enumerate(samples) for j, right in enumerate(samples) if i < j
        ]
        outdir = args.outdir
        figures = outdir / "figures"
        outdir.mkdir(parents=True, exist_ok=True)
        figures.mkdir(exist_ok=True)
        write_rows(outdir / "pairwise_correlations.tsv", correlations)
        pd.DataFrame({"protein": cv.index, "cv": cv.values}).to_csv(
            outdir / "protein_cv.tsv", sep="\t", index=False, lineterminator="\n")
        with (outdir / "protein_cv.summary.tsv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(("field", "value"))
            writer.writerows(cv_summary.items())
        write_rows(outdir / "pca_scores.tsv", pca_rows)
        with (outdir / "pca_variance.tsv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(("component", "explained_variance_fraction"))
            writer.writerow(("PC1", explained[0]))
            writer.writerow(("PC2", explained[1]))
        write_rows(outdir / "sample_distances.tsv", distance_rows)

        plt.rcParams.update({"font.size": 10})
        fig, ax = plt.subplots(figsize=(5.5, 4.8), constrained_layout=True)
        image = ax.imshow(pearson_matrix, vmin=0.9, vmax=1.0, cmap="GnBu")
        labels = [short(sample) for sample in samples]
        ax.set_xticks(range(len(samples)), labels)
        ax.set_yticks(range(len(samples)), labels)
        for i in range(len(samples)):
            for j in range(len(samples)):
                ax.text(j, i, f"{pearson_matrix.iloc[i, j]:.3f}", ha="center", va="center", color="#222222")
        ax.set_xlabel("Technical run")
        ax.set_ylabel("Technical run")
        fig.colorbar(image, ax=ax, label="Pearson r")
        fig.savefig(figures / "sample_correlation_matrix.png", dpi=180, facecolor="white")
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(6.5, 4.2), constrained_layout=True)
        ax.hist(cv, bins=45, color="#76B7B2", edgecolor="white")
        ax.axvline(cv.median(), color="#D3726C", linewidth=1.7, label=f"Median = {cv.median():.3f}")
        ax.set_xlabel("Protein CV (sample SD / mean)")
        ax.set_ylabel("Complete proteins")
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False)
        fig.savefig(figures / "protein_cv_distribution.png", dpi=180, facecolor="white")
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(6, 4.8), constrained_layout=True)
        for index, row in enumerate(pca_rows):
            ax.scatter(row["PC1"], row["PC2"], s=65, color=("#4C78A8", "#59A14F", "#F28E2B")[index])
            ax.annotate(short(str(row["sample"])), (row["PC1"], row["PC2"]), xytext=(6, 5), textcoords="offset points")
        ax.axhline(0, color="#CCCCCC", linewidth=0.8)
        ax.axvline(0, color="#CCCCCC", linewidth=0.8)
        ax.set_xlabel(f"PC1 ({explained[0] * 100:.1f}%)")
        ax.set_ylabel(f"PC2 ({explained[1] * 100:.1f}%)")
        ax.spines[["top", "right"]].set_visible(False)
        fig.savefig(figures / "pca_technical_qc.png", dpi=180, facecolor="white")
        plt.close(fig)
    except (OSError, UnicodeError, ValueError, KeyError, pd.errors.ParserError) as exc:
        print(f"exploratory-analysis error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
