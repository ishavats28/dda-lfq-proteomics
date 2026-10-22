#!/usr/bin/env python3
"""Validate a local IonQuant mzML/Philosopher-report manifest."""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from pathlib import Path


REQUIRED = ("sample", "mzml", "psm", "protein")
SAMPLE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
PSM_COLUMNS = {"Spectrum", "Peptide", "Protein", "PeptideProphet Probability"}


def readable_file(path: Path, label: str, row: int) -> Path:
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError(f"row {row}: {label} does not exist: {path}") from exc
    if not resolved.is_file() or not os.access(resolved, os.R_OK):
        raise ValueError(f"row {row}: {label} is not a readable regular file: {resolved}")
    if resolved.stat().st_size == 0:
        raise ValueError(f"row {row}: {label} is empty: {resolved}")
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--base-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        source = args.input.resolve(strict=True)
        base = args.base_dir.resolve(strict=True)
        with source.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if reader.fieldnames is None:
                raise ValueError("quantification manifest has no header")
            missing = [column for column in REQUIRED if column not in reader.fieldnames]
            if missing:
                raise ValueError("missing required column(s): " + ", ".join(missing))
            if len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise ValueError("quantification manifest contains duplicate column names")
            rows = list(reader)
        if not rows:
            raise ValueError("quantification manifest contains no data rows")
        normalized: list[dict[str, str]] = []
        samples: set[str] = set()
        mzml_paths: set[Path] = set()
        for number, row in enumerate(rows, start=2):
            if None in row:
                raise ValueError(f"row {number}: too many tab-separated fields")
            sample = (row.get("sample") or "").strip()
            if not SAMPLE.fullmatch(sample):
                raise ValueError(f"row {number}: sample '{sample}' is not filesystem-safe")
            if sample in samples:
                raise ValueError(f"row {number}: duplicate sample ID '{sample}'")
            samples.add(sample)
            mzml_value = (row.get("mzml") or "").strip()
            psm_value = (row.get("psm") or "").strip()
            protein_value = (row.get("protein") or "").strip()
            if not mzml_value or not psm_value or not protein_value:
                raise ValueError(
                    f"row {number} sample '{sample}': mzml, psm, and protein must be non-empty"
                )
            if "://" in mzml_value or "://" in psm_value or "://" in protein_value:
                raise ValueError(f"row {number} sample '{sample}': URLs are not accepted")
            mzml = readable_file(base / mzml_value, "mzML", number)
            psm = readable_file(base / psm_value, "psm.tsv", number)
            protein = readable_file(base / protein_value, "protein.tsv", number)
            if mzml.suffix != ".mzML":
                raise ValueError(f"row {number} sample '{sample}': mzML path must end in .mzML")
            if psm.name != "psm.tsv":
                raise ValueError(f"row {number} sample '{sample}': PSM report must be named psm.tsv")
            if protein.name != "protein.tsv":
                raise ValueError(f"row {number} sample '{sample}': protein report must be named protein.tsv")
            if mzml in mzml_paths:
                raise ValueError(f"row {number} sample '{sample}': duplicate resolved mzML path")
            mzml_paths.add(mzml)
            with psm.open(encoding="utf-8", newline="") as handle:
                report = csv.reader(handle, delimiter="\t")
                header = next(report, [])
                first = next(report, None)
            absent = sorted(PSM_COLUMNS - set(header))
            if absent:
                raise ValueError(
                    f"row {number} sample '{sample}': psm.tsv missing required column(s): {', '.join(absent)}"
                )
            if first is None:
                raise ValueError(f"row {number} sample '{sample}': psm.tsv has no PSM rows")
            with protein.open(encoding="utf-8", newline="") as handle:
                protein_report = csv.reader(handle, delimiter="\t")
                protein_header = next(protein_report, [])
                protein_first = next(protein_report, None)
            if "Protein" not in protein_header:
                raise ValueError(f"row {number} sample '{sample}': protein.tsv missing Protein column")
            if protein_first is None:
                raise ValueError(f"row {number} sample '{sample}': protein.tsv has no protein rows")
            normalized.append(
                {"sample": sample, "mzml": str(mzml), "psm": str(psm), "protein": str(protein)}
            )
        with args.output.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(REQUIRED), delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(normalized)
    except (FileNotFoundError, OSError, UnicodeError, ValueError, csv.Error) as exc:
        print(f"IonQuant input validation error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
