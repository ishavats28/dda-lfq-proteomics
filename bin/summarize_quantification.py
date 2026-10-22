#!/usr/bin/env python3
"""Summarize IonQuant report structure without recalculating quantification."""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
import statistics
import sys
from pathlib import Path


def rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames:
            raise ValueError(f"IonQuant report has no header: {path}")
        data = list(reader)
    if not data:
        raise ValueError(f"IonQuant report has no data rows: {path}")
    return reader.fieldnames, data


def numeric(value: str) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--ionquant-version", default="1.11.20")
    parser.add_argument("--mbr", choices=("on", "off"), required=True)
    parser.add_argument("--mzml-sha256", default="NA")
    parser.add_argument("--fasta-sha256", default="NA")
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    try:
        root = args.reports.resolve(strict=True)
        if not root.is_dir():
            raise ValueError(f"IonQuant reports path is not a directory: {root}")
        report_paths: dict[str, list[Path]] = {
            name: sorted((root / "runs").glob(f"*/{name}.tsv")) for name in ("ion", "peptide", "protein")
        }
        if not any(report_paths.values()):
            report_paths = {name: sorted(root.glob(f"{name}.tsv")) for name in report_paths}
        missing = [name for name, paths in report_paths.items() if not paths]
        if missing:
            raise ValueError("missing non-empty IonQuant report type(s): " + ", ".join(missing))
        parsed: dict[str, list[dict[str, str]]] = {}
        headers: dict[str, list[str]] = {}
        for name, paths in report_paths.items():
            combined: list[dict[str, str]] = []
            columns: list[str] = []
            for path in paths:
                if path.stat().st_size == 0:
                    raise ValueError(f"IonQuant report is empty: {path}")
                current_columns, current_rows = rows(path)
                columns = current_columns
                combined.extend(current_rows)
            headers[name] = columns
            parsed[name] = combined

        combined: dict[str, tuple[list[str], list[dict[str, str]]]] = {}
        for name in ("ion", "peptide", "protein"):
            path = root / "combined" / f"combined_{name}.tsv"
            if path.is_file() and path.stat().st_size:
                combined[name] = rows(path)

        has_combined_protein = "protein" in combined
        protein_headers, protein_rows = combined.get(
            "protein", (headers["protein"], parsed["protein"])
        )
        if has_combined_protein:
            maxlfq = [column for column in protein_headers if column.endswith(" MaxLFQ Intensity")]
            protein_intensity = [
                column for column in protein_headers
                if column.endswith(" Intensity") and "MaxLFQ" not in column
            ]
        else:
            maxlfq = [column for column in protein_headers if "maxlfq" in column.lower()]
            protein_intensity = [
                column for column in protein_headers
                if "intensity" in column.lower() and "maxlfq" not in column.lower()
            ]
        values = [
            number
            for row in protein_rows
            for column in protein_intensity
            if (number := numeric(row.get(column, ""))) is not None and number > 0
        ]
        missing_values = sum(
            1
            for row in protein_rows
            for column in protein_intensity
            if (numeric(row.get(column, "")) or 0) <= 0
        )
        maxlfq_proteins = sum(
            1
            for row in protein_rows
            if any((numeric(row.get(column, "")) or 0) > 0 for column in maxlfq)
        )
        mzml_hashes: list[str] = []
        psm_hashes: list[str] = []
        if args.manifest:
            with args.manifest.open(encoding="utf-8", newline="") as handle:
                for manifest_row in csv.DictReader(handle, delimiter="\t"):
                    path = Path(manifest_row["mzml"])
                    digest = hashlib.sha256()
                    with path.open("rb") as binary:
                        for block in iter(lambda: binary.read(1024 * 1024), b""):
                            digest.update(block)
                    mzml_hashes.append(f"{manifest_row['sample']}={digest.hexdigest()}")
                    psm_digest = hashlib.sha256()
                    with Path(manifest_row["psm"]).open("rb") as binary:
                        for block in iter(lambda: binary.read(1024 * 1024), b""):
                            psm_digest.update(block)
                    psm_hashes.append(f"{manifest_row['sample']}={psm_digest.hexdigest()}")
        quantified_proteins = len(protein_rows)
        common_proteins = sum(
            1 for row in protein_rows
            if protein_intensity and all((numeric(row.get(column, "")) or 0) > 0 for column in protein_intensity)
        )
        fields = {
            "runs_processed": len(protein_intensity),
            "quantified_ions": len(combined.get("ion", ([], parsed["ion"]))[1]),
            "quantified_peptides": len(combined.get("peptide", ([], parsed["peptide"]))[1]),
            "quantified_proteins": quantified_proteins,
            "maxlfq_proteins": maxlfq_proteins,
            "proteins_quantified_across_all_runs": common_proteins,
            "protein_intensity_fields": len(protein_intensity) * quantified_proteins,
            "missing_or_zero_protein_intensities": missing_values,
            "protein_missingness_fraction": (
                missing_values / (len(protein_intensity) * quantified_proteins)
                if protein_intensity and quantified_proteins else "NA"
            ),
            "minimum_nonzero_intensity": min(values) if values else "NA",
            "maximum_nonzero_intensity": max(values) if values else "NA",
            "median_nonzero_intensity": statistics.median(values) if values else "NA",
            "mbr": args.mbr,
            "ionquant_version": args.ionquant_version,
            "mzml_sha256": ";".join(mzml_hashes) if mzml_hashes else args.mzml_sha256,
            "psm_sha256": ";".join(psm_hashes) if psm_hashes else "NA",
            "fasta_sha256": args.fasta_sha256,
        }
        for column in protein_intensity:
            sample = column.removesuffix(" Intensity")
            nonzero = [(numeric(row.get(column, "")) or 0) for row in protein_rows]
            nonzero = [value for value in nonzero if value > 0]
            fields[f"{sample}.quantified_proteins"] = len(nonzero)
            fields[f"{sample}.missing_proteins"] = quantified_proteins - len(nonzero)
            fields[f"{sample}.median_nonzero_intensity"] = statistics.median(nonzero) if nonzero else "NA"
        with args.output.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(("field", "value"))
            writer.writerows(fields.items())
    except (FileNotFoundError, OSError, UnicodeError, ValueError, csv.Error) as exc:
        print(f"IonQuant summary error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
