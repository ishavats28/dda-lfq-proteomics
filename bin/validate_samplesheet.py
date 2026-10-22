#!/usr/bin/env python3
"""Validate and normalize the workflow TSV sample sheet."""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from pathlib import Path


REQUIRED_COLUMNS = ("sample", "condition", "replicate", "mzml")
OPTIONAL_COLUMNS = ("batch", "fraction")
OUTPUT_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS
SAFE_SAMPLE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
URL = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")


class ContractError(ValueError):
    """A concise, user-correctable sample-sheet error."""


def row_label(row_number: int, sample: str | None) -> str:
    if sample:
        return f"row {row_number} (sample '{sample}')"
    return f"row {row_number}"


def reject_control_characters(value: str, field: str, label: str) -> None:
    if "\n" in value or "\r" in value or "\x00" in value:
        raise ContractError(f"{label}: column '{field}' contains a forbidden control character")


def resolve_mzml(raw_path: str, base_dir: Path, label: str) -> Path:
    if not raw_path:
        raise ContractError(f"{label}: column 'mzml' is empty")
    if URL.match(raw_path):
        raise ContractError(f"{label}: mzML URLs are not supported: {raw_path}")

    candidate = Path(raw_path)
    if candidate.suffix.lower() != ".mzml":
        raise ContractError(f"{label}: mzML path must end in .mzML: {raw_path}")
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    resolved = candidate.resolve(strict=False)

    if not resolved.exists():
        raise ContractError(f"{label}: mzML file does not exist: {resolved}")
    if not resolved.is_file():
        raise ContractError(f"{label}: mzML path is not a regular file: {resolved}")
    if not os.access(resolved, os.R_OK):
        raise ContractError(f"{label}: mzML file is not readable: {resolved}")
    try:
        with resolved.open("rb") as handle:
            handle.read(1)
    except OSError as exc:
        raise ContractError(f"{label}: mzML file is not readable: {resolved}: {exc.strerror}") from exc
    return resolved


def validate(input_path: Path, output_path: Path, base_dir: Path | None = None) -> int:
    source = input_path.resolve(strict=True)
    resolution_base = (base_dir or source.parent).resolve(strict=True)

    try:
        handle = source.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise ContractError(f"cannot read sample sheet '{source}': {exc.strerror}") from exc

    normalized: list[dict[str, str]] = []
    seen_samples: dict[str, int] = {}
    seen_paths: dict[Path, tuple[int, str]] = {}

    with handle:
        reader = csv.reader(handle, delimiter="\t", strict=True)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ContractError("sample sheet is empty") from exc
        except csv.Error as exc:
            raise ContractError(f"invalid TSV header: {exc}") from exc

        if len(header) != len(set(header)):
            raise ContractError("sample sheet header contains duplicate column names")
        missing = [column for column in REQUIRED_COLUMNS if column not in header]
        if missing:
            raise ContractError(f"sample sheet is missing required column(s): {', '.join(missing)}")
        unknown = [column for column in header if column not in OUTPUT_COLUMNS]
        if unknown:
            raise ContractError(f"sample sheet contains unsupported column(s): {', '.join(unknown)}")

        for row_number, fields in enumerate(reader, start=2):
            if not fields or all(not field.strip() for field in fields):
                continue
            if len(fields) != len(header):
                raise ContractError(
                    f"row {row_number}: expected {len(header)} tab-separated fields, found {len(fields)}"
                )

            row = {column: value.strip() for column, value in zip(header, fields, strict=True)}
            sample = row.get("sample", "")
            label = row_label(row_number, sample)
            for field, value in row.items():
                reject_control_characters(value, field, label)

            if not sample:
                raise ContractError(f"row {row_number}: column 'sample' is empty")
            if not SAFE_SAMPLE.fullmatch(sample):
                raise ContractError(
                    f"{label}: sample must start with an alphanumeric character and contain only letters, digits, '.', '_' or '-'"
                )
            if sample in seen_samples:
                raise ContractError(
                    f"{label}: duplicate sample ID; first used at row {seen_samples[sample]}"
                )
            seen_samples[sample] = row_number

            if not row["condition"]:
                raise ContractError(f"{label}: column 'condition' is empty")

            replicate_text = row["replicate"]
            if not replicate_text.isdecimal() or int(replicate_text) <= 0:
                raise ContractError(f"{label}: replicate must be a positive integer: {replicate_text or '<empty>'}")

            resolved_mzml = resolve_mzml(row["mzml"], resolution_base, label)
            if resolved_mzml in seen_paths:
                first_row, first_sample = seen_paths[resolved_mzml]
                raise ContractError(
                    f"{label}: duplicate resolved mzML path; first used by sample '{first_sample}' at row {first_row}: {resolved_mzml}"
                )
            seen_paths[resolved_mzml] = (row_number, sample)

            normalized.append(
                {
                    "sample": sample,
                    "condition": row["condition"],
                    "replicate": str(int(replicate_text)),
                    "mzml": str(resolved_mzml),
                    "batch": row.get("batch", ""),
                    "fraction": row.get("fraction", ""),
                }
            )

    if not normalized:
        raise ContractError("sample sheet contains no data rows")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(output_path.name + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(normalized)
        temporary.replace(output_path)
    finally:
        temporary.unlink(missing_ok=True)
    return len(normalized)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Input TSV sample sheet")
    parser.add_argument("--output", required=True, type=Path, help="Normalized output TSV")
    parser.add_argument("--base-dir", type=Path, help="Base directory for relative mzML paths")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        count = validate(args.input, args.output, args.base_dir)
    except (ContractError, OSError, csv.Error) as exc:
        print(f"sample-sheet validation error: {exc}", file=sys.stderr)
        return 2
    print(f"validated {count} sample(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
