#!/usr/bin/env python3
"""Validate the MSFragger native-resource directory required by IonQuant."""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path


LINUX_TIMSDATA = "libtimsdata-2-21-0-4.so"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ext", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        if not args.ext.exists():
            raise ValueError(f"MSFragger ext directory does not exist: {args.ext}")
        ext = args.ext.resolve(strict=True)
        if not ext.is_dir():
            raise ValueError(f"MSFragger ext path is not a directory: {ext}")
        if not os.access(ext, os.R_OK | os.X_OK):
            raise ValueError(f"MSFragger ext directory is not readable: {ext}")
        native = list(ext.rglob(LINUX_TIMSDATA))
        if len(native) != 1 or not native[0].is_file():
            raise ValueError(
                f"MSFragger ext directory must contain exactly one {LINUX_TIMSDATA} for Linux IonQuant"
            )
        args.output.write_text(
            "field\tvalue\n"
            f"resource\t{LINUX_TIMSDATA}\n"
            f"sha256\t{sha256(native[0])}\n"
            "validation_status\tok\n",
            encoding="utf-8",
        )
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"IonQuant ext validation error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
