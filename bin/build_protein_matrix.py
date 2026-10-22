#!/usr/bin/env python3
"""Build filtered raw and log2 protein-by-sample MaxLFQ matrices."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ANNOTATION_COLUMNS = ("Protein ID", "Entry Name", "Gene", "Description", "Combined Total Peptides")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protein", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    args = parser.parse_args()
    try:
        source = pd.read_csv(args.protein.resolve(strict=True), sep="\t", dtype=str, keep_default_na=False)
        if "Protein" not in source.columns:
            raise ValueError("IonQuant protein table lacks the Protein column")
        intensity_columns = [column for column in source.columns if column.endswith(" MaxLFQ Intensity")]
        if not intensity_columns:
            raise ValueError("IonQuant protein table contains no MaxLFQ intensity columns")
        samples = [column.removesuffix(" MaxLFQ Intensity") for column in intensity_columns]
        if len(samples) != len(set(samples)):
            raise ValueError("duplicate MaxLFQ sample columns")
        if source["Protein"].eq("").any():
            raise ValueError("protein table contains an empty protein identifier")
        duplicates = source.loc[source["Protein"].duplicated(keep=False), "Protein"].unique()
        if len(duplicates):
            raise ValueError("duplicate protein identifier/group: " + ", ".join(sorted(duplicates)[:5]))
        identifiers = source["Protein"].astype(str)
        decoy = identifiers.str.startswith("rev_")
        contaminant = identifiers.str.startswith("contam_")
        numeric = source[intensity_columns].apply(pd.to_numeric, errors="coerce")
        numeric = numeric.mask(numeric <= 0)
        all_missing = numeric.isna().all(axis=1)
        retain = ~(decoy | contaminant | all_missing)
        matrix = numeric.loc[retain].copy()
        matrix.columns = samples
        matrix.insert(0, "protein", identifiers.loc[retain].values)
        log2 = matrix.copy()
        log2[samples] = np.log2(log2[samples])
        annotation_columns = [column for column in ANNOTATION_COLUMNS if column in source.columns]
        annotations = source.loc[retain, ["Protein", *annotation_columns]].copy()
        annotations = annotations.rename(columns={"Protein": "protein"})
        annotations.insert(1, "is_decoy", "false")
        annotations.insert(2, "is_contaminant", "false")
        outdir = args.outdir
        outdir.mkdir(parents=True, exist_ok=True)
        matrix.to_csv(outdir / "protein_matrix.raw.tsv", sep="\t", index=False, na_rep="", lineterminator="\n")
        log2.to_csv(outdir / "protein_matrix.log2.tsv", sep="\t", index=False, na_rep="", lineterminator="\n")
        annotations.to_csv(outdir / "protein_annotations.tsv", sep="\t", index=False, lineterminator="\n")
        summary = {
            "starting_protein_rows": len(source),
            "decoy_rows_removed": int(decoy.sum()),
            "contaminant_rows_removed": int(contaminant.sum()),
            "unquantified_rows_removed": int((all_missing & ~decoy & ~contaminant).sum()),
            "final_analytical_rows": len(matrix),
            "sample_columns": len(samples),
            "samples": ";".join(samples),
            "value": "MaxLFQ intensity",
            "log2_policy": "positive values transformed; zero and missing remain missing; no pseudocount",
        }
        with (outdir / "protein_matrix.summary.tsv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(("field", "value"))
            writer.writerows(summary.items())
    except (OSError, UnicodeError, ValueError, pd.errors.ParserError) as exc:
        print(f"protein-matrix error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
