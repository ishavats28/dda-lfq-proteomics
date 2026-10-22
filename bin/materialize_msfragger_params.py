#!/usr/bin/env python3
"""Materialize one validated FASTA path into an MSFragger parameter template."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PLACEHOLDER = "__DATABASE_NAME__"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    try:
        # Keep a staged task-local symlink path task-local.  Resolving the
        # symlink would let MSFragger write its peptide index beside the
        # original database instead of inside the disposable work directory.
        database = args.database.absolute()
        if not database.exists():
            raise ValueError(f"database does not exist: {database}")
        if not database.is_file():
            raise ValueError(f"database is not a regular file: {database}")
        lines = args.template.read_text(encoding="utf-8").splitlines(keepends=True)
        active = [
            index for index, line in enumerate(lines)
            if not line.lstrip().startswith("#") and PLACEHOLDER in line
        ]
        count = len(active)
        if count != 1:
            raise ValueError(f"parameter template must contain {PLACEHOLDER} exactly once; found {count}")
        index = active[0]
        setting = lines[index].split("#", 1)[0]
        if not setting.lstrip().startswith("database_name") or setting.count(PLACEHOLDER) != 1:
            raise ValueError(f"{PLACEHOLDER} must occur once in the active database_name setting")
        lines[index] = lines[index].replace(PLACEHOLDER, str(database), 1)
        materialized = "".join(lines)
        temporary = args.output.with_name(args.output.name + ".tmp")
        temporary.write_text(materialized, encoding="utf-8", newline="\n")
        temporary.replace(args.output)
    except (OSError, ValueError) as exc:
        print(f"MSFragger parameter error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
