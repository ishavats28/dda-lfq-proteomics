#!/usr/bin/env python3
"""Create or verify a deterministic protein-database cache manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path


FIELDS = (
    "database_id", "source", "source_accession", "taxonomy_id", "organism",
    "review_status", "generation_utc", "philosopher_version", "contaminants",
    "decoy_strategy", "decoy_prefix", "target_count", "decoy_count",
    "contaminant_count", "final_sha256", "final_bytes", "filename",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fasta_counts(path: Path, decoy_prefix: str, contaminant_prefix: str) -> tuple[int, int, int]:
    targets = decoys = contaminants = 0
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.startswith(">"):
                continue
            identifier = line[1:].strip().split(maxsplit=1)[0]
            if not identifier:
                raise ValueError(f"empty FASTA identifier at line {line_number}")
            undecoyed = identifier[len(decoy_prefix):] if identifier.startswith(decoy_prefix) else identifier
            if identifier.startswith(decoy_prefix):
                decoys += 1
            else:
                targets += 1
            if undecoyed.startswith(contaminant_prefix):
                contaminants += 1
    if targets + decoys == 0:
        raise ValueError("FASTA contains no records")
    return targets, decoys, contaminants


def read_manifest(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if len(rows) != 1 or tuple(rows[0]) != FIELDS:
        raise ValueError("database manifest must contain exactly one row with the documented columns")
    return rows[0]


def create(args: argparse.Namespace) -> None:
    fasta = args.fasta.resolve(strict=True)
    if not fasta.is_file() or fasta.stat().st_size == 0:
        raise ValueError(f"database FASTA is absent or empty: {fasta}")
    target, decoy, contaminant = fasta_counts(fasta, args.decoy_prefix, args.contaminant_prefix)
    record = {
        "database_id": args.database_id,
        "source": args.source,
        "source_accession": args.source_accession,
        "taxonomy_id": args.taxonomy_id,
        "organism": args.organism,
        "review_status": args.review_status,
        "generation_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "philosopher_version": args.philosopher_version,
        "contaminants": args.contaminants,
        "decoy_strategy": args.decoy_strategy,
        "decoy_prefix": args.decoy_prefix,
        "target_count": str(target),
        "decoy_count": str(decoy),
        "contaminant_count": str(contaminant),
        "final_sha256": sha256(fasta),
        "final_bytes": str(fasta.stat().st_size),
        "filename": fasta.name,
    }
    temporary = args.manifest.with_suffix(args.manifest.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerow(record)
    temporary.replace(args.manifest)


def verify(args: argparse.Namespace) -> None:
    fasta = args.fasta.resolve(strict=True)
    manifest = read_manifest(args.manifest.resolve(strict=True))
    actual_hash = sha256(fasta)
    if manifest["filename"] != fasta.name:
        raise ValueError(f"database cache filename mismatch: manifest={manifest['filename']}, actual={fasta.name}")
    if manifest["final_sha256"].lower() != actual_hash:
        raise ValueError(
            f"database cache checksum mismatch for {fasta.name}: "
            f"manifest={manifest['final_sha256']}, actual={actual_hash}"
        )
    if manifest["final_bytes"] != str(fasta.stat().st_size):
        raise ValueError("database cache byte-size mismatch")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)
    for name in ("create", "verify"):
        command = sub.add_parser(name)
        command.add_argument("--fasta", required=True, type=Path)
        command.add_argument("--manifest", required=True, type=Path)
        if name == "create":
            command.add_argument("--database-id", required=True)
            command.add_argument("--source", required=True)
            command.add_argument("--source-accession", required=True)
            command.add_argument("--taxonomy-id", required=True)
            command.add_argument("--organism", required=True)
            command.add_argument("--review-status", required=True)
            command.add_argument("--philosopher-version", required=True)
            command.add_argument("--contaminants", required=True)
            command.add_argument("--decoy-strategy", required=True)
            command.add_argument("--decoy-prefix", required=True)
            command.add_argument("--contaminant-prefix", default="contam_")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        create(args) if args.command == "create" else verify(args)
    except (OSError, ValueError, csv.Error) as exc:
        print(f"database cache error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
