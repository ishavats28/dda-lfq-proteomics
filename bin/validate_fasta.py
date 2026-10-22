#!/usr/bin/env python3
"""Validate a protein FASTA file and write a deterministic TSV manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sys
from pathlib import Path


ACCEPTED_EXTENSIONS = {".fa", ".faa", ".fasta"}
PROTEIN_ALPHABET = frozenset("ACDEFGHIKLMNPQRSTVWYBXZJUO")
MANIFEST_FIELDS = (
    "filename",
    "resolved_path",
    "record_count",
    "total_amino_acids",
    "sha256",
    "validation_status",
)


class FastaError(ValueError):
    """A deterministic, user-correctable FASTA contract error."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_fasta(input_path: Path) -> dict[str, str | int]:
    try:
        resolved = input_path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise FastaError(f"FASTA file does not exist: {input_path}") from exc

    if not resolved.is_file():
        raise FastaError(f"FASTA path is not a regular file: {resolved}")
    if resolved.suffix.lower() not in ACCEPTED_EXTENSIONS:
        allowed = ", ".join(sorted(ACCEPTED_EXTENSIONS))
        raise FastaError(f"FASTA extension must be one of {allowed}: {resolved.name}")
    if not os.access(resolved, os.R_OK):
        raise FastaError(f"FASTA file is not readable: {resolved}")
    if resolved.stat().st_size == 0:
        raise FastaError(f"FASTA file is empty: {resolved}")

    identifiers: dict[str, int] = {}
    current_identifier: str | None = None
    current_header_line = 0
    current_length = 0
    record_count = 0
    total_amino_acids = 0

    with resolved.open("r", encoding="utf-8", newline=None) as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if current_identifier is not None and current_length == 0:
                    raise FastaError(
                        f"record '{current_identifier}' from line {current_header_line} has an empty sequence"
                    )
                header = line[1:].strip()
                if not header:
                    raise FastaError(f"line {line_number}: FASTA header is empty")
                identifier = header.split(maxsplit=1)[0]
                if identifier in identifiers:
                    raise FastaError(
                        f"line {line_number}: duplicate FASTA identifier '{identifier}'; first used at line {identifiers[identifier]}"
                    )
                identifiers[identifier] = line_number
                current_identifier = identifier
                current_header_line = line_number
                current_length = 0
                record_count += 1
                continue

            if current_identifier is None:
                raise FastaError(f"line {line_number}: sequence data appears before the first FASTA header")
            sequence = line.upper()
            invalid = sorted(set(sequence) - PROTEIN_ALPHABET)
            if invalid:
                display = "".join(invalid)
                raise FastaError(
                    f"line {line_number}, record '{current_identifier}': invalid protein sequence character(s): {display}"
                )
            current_length += len(sequence)
            total_amino_acids += len(sequence)

    if record_count == 0:
        raise FastaError(f"FASTA contains no records: {resolved}")
    if current_identifier is not None and current_length == 0:
        raise FastaError(f"record '{current_identifier}' from line {current_header_line} has an empty sequence")

    return {
        "filename": resolved.name,
        "resolved_path": str(resolved),
        "record_count": record_count,
        "total_amino_acids": total_amino_acids,
        "sha256": file_sha256(resolved),
        "validation_status": "ok",
    }


def write_manifest(record: dict[str, str | int], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(output_path.name + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerow(record)
        temporary.replace(output_path)
    finally:
        temporary.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        record = validate_fasta(args.input)
        write_manifest(record, args.output)
    except (FastaError, OSError, UnicodeError) as exc:
        print(f"FASTA validation error: {exc}", file=sys.stderr)
        return 2
    print(f"validated {record['record_count']} FASTA record(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
