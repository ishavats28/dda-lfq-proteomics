#!/usr/bin/env python3
"""Create a descriptive summary from genuine search and Philosopher outputs."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path


def table(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"required report is absent or empty: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames:
            raise ValueError(f"report has no header: {path}")
        return reader.fieldnames, list(reader)


def qc_values(path: Path) -> dict[str, str]:
    _, rows = table(path)
    if len(rows) != 1:
        raise ValueError("mzML QC input must contain exactly one data row")
    return rows[0]


def raw_psm_count(path: Path) -> int:
    count = 0
    with path.open(encoding="utf-8", errors="strict") as handle:
        for line in handle:
            count += line.count("<spectrum_query ")
    if count == 0:
        raise ValueError(f"raw pepXML contains no spectrum_query records: {path}")
    return count


def manifest_sha256(path: Path) -> str:
    _, rows = table(path)
    if len(rows) != 1 or "sha256" not in rows[0]:
        raise ValueError("FASTA validation manifest must contain one row and a sha256 column")
    value = rows[0]["sha256"].lower()
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("FASTA validation manifest contains an invalid sha256 value")
    return value


def find_column(headers: list[str], candidates: tuple[str, ...], label: str) -> str:
    normalized = {re.sub(r"[^a-z0-9]", "", header.lower()): header for header in headers}
    for candidate in candidates:
        key = re.sub(r"[^a-z0-9]", "", candidate.lower())
        if key in normalized:
            return normalized[key]
    raise ValueError(f"cannot locate {label} column; available columns: {', '.join(headers)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", required=True)
    parser.add_argument("--mzml-qc", required=True, type=Path)
    parser.add_argument("--raw-pepxml", required=True, type=Path)
    parser.add_argument("--psm", required=True, type=Path)
    parser.add_argument("--peptide", required=True, type=Path)
    parser.add_argument("--protein", required=True, type=Path)
    parser.add_argument("--decoy-prefix", default="rev_")
    parser.add_argument("--psm-fdr", default="0.01")
    parser.add_argument("--peptide-fdr", default="0.01")
    parser.add_argument("--protein-fdr", default="0.01")
    parser.add_argument("--msfragger-version", default="4.4.1")
    parser.add_argument("--philosopher-version", default="5.1.0")
    parser.add_argument("--database-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        qc = qc_values(args.mzml_qc)
        psm_headers, psms = table(args.psm)
        _, peptides = table(args.peptide)
        _, proteins = table(args.protein)
        protein_column = find_column(psm_headers, ("Protein", "Protein ID", "ProteinID"), "PSM protein")
        decoys = sum(row[protein_column].startswith(args.decoy_prefix) for row in psms)
        record = {
            "sample": args.sample,
            "total_spectra": qc["total_spectra"],
            "ms2_spectra": qc["ms2_spectra"],
            "raw_msfragger_psms": str(raw_psm_count(args.raw_pepxml)),
            "filtered_psms": str(len(psms)),
            "unique_peptides": str(len(peptides)),
            "protein_groups_or_proteins": str(len(proteins)),
            "target_psms": str(len(psms) - decoys),
            "decoy_psms": str(decoys),
            "psm_fdr": args.psm_fdr,
            "peptide_fdr": args.peptide_fdr,
            "protein_fdr": args.protein_fdr,
            "msfragger_version": args.msfragger_version,
            "philosopher_version": args.philosopher_version,
            "database_sha256": manifest_sha256(args.database_manifest),
        }
        with args.output.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=record, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerow(record)
    except (OSError, ValueError, KeyError, csv.Error) as exc:
        args.output.unlink(missing_ok=True)
        print(f"identification summary error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
