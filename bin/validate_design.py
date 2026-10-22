#!/usr/bin/env python3
"""Validate an experimental design against quantitative sample columns."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path


REQUIRED = ("sample", "condition", "replicate")
OPTIONAL = ("batch", "subject", "fraction")
SAFE_SAMPLE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def matrix_samples(path: Path) -> list[str]:
    with path.open(encoding="utf-8", newline="") as handle:
        header = next(csv.reader(handle, delimiter="\t"), [])
    if not header or header[0] != "protein":
        raise ValueError("matrix must begin with a 'protein' column")
    samples = header[1:]
    if not samples or len(samples) != len(set(samples)):
        raise ValueError("matrix sample columns must be present and unique")
    return samples


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", required=True, type=Path)
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()
    try:
        quantitative_samples = matrix_samples(args.matrix.resolve(strict=True))
        with args.design.resolve(strict=True).open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if reader.fieldnames is None:
                raise ValueError("design table has no header")
            missing = [field for field in REQUIRED if field not in reader.fieldnames]
            if missing:
                raise ValueError("missing required design column(s): " + ", ".join(missing))
            unknown = [field for field in reader.fieldnames if field not in REQUIRED + OPTIONAL]
            if unknown:
                raise ValueError("unsupported design column(s): " + ", ".join(unknown))
            rows = list(reader)
        if not rows:
            raise ValueError("design table contains no samples")
        normalized: list[dict[str, str]] = []
        observed: set[str] = set()
        for number, row in enumerate(rows, start=2):
            if None in row:
                raise ValueError(f"row {number}: too many tab-separated fields")
            sample = (row.get("sample") or "").strip()
            condition = (row.get("condition") or "").strip()
            replicate = (row.get("replicate") or "").strip()
            if not SAFE_SAMPLE.fullmatch(sample):
                raise ValueError(f"row {number}: sample '{sample}' is not filesystem-safe")
            if sample in observed:
                raise ValueError(f"row {number}: duplicate sample '{sample}'")
            if sample not in quantitative_samples:
                raise ValueError(f"row {number}: sample '{sample}' is absent from the quantitative matrix")
            if not condition:
                raise ValueError(f"row {number} sample '{sample}': condition must be non-empty")
            try:
                replicate_number = int(replicate)
            except ValueError as exc:
                raise ValueError(f"row {number} sample '{sample}': replicate must be a positive integer") from exc
            if replicate_number <= 0 or str(replicate_number) != replicate:
                raise ValueError(f"row {number} sample '{sample}': replicate must be a positive integer")
            observed.add(sample)
            normalized.append({field: (row.get(field) or "").strip() for field in REQUIRED + OPTIONAL})
        absent = [sample for sample in quantitative_samples if sample not in observed]
        if absent and not args.allow_incomplete:
            raise ValueError("quantitative sample(s) absent from complete design: " + ", ".join(absent))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(REQUIRED + OPTIONAL), delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(normalized)
    except (OSError, UnicodeError, ValueError, csv.Error) as exc:
        print(f"design validation error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
