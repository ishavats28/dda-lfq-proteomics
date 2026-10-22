#!/usr/bin/env python3
"""Check single-file download size and free-space policy."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


GIB = 1024**3


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-bytes", required=True, type=int)
    parser.add_argument("--path", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.remote_bytes <= 0:
            raise ValueError("remote size must be a positive integer")
        free = shutil.disk_usage(args.path.resolve(strict=True)).free
        required = args.remote_bytes * 4 + 15 * GIB
        reasons: list[str] = []
        if args.remote_bytes > 4 * GIB:
            reasons.append("remote file exceeds the 4 GiB single-file limit")
        if free < required:
            reasons.append("free disk is below four times the object size plus 15 GiB")
        status = "fail" if reasons else "pass"
        args.output.write_text(
            "metric\tvalue\n"
            f"remote_bytes\t{args.remote_bytes}\n"
            f"disk_free_bytes\t{free}\n"
            f"required_free_bytes\t{required}\n"
            f"status\t{status}\n",
            encoding="utf-8",
        )
        if reasons:
            raise ValueError("; ".join(reasons))
    except (OSError, ValueError) as exc:
        print(f"download preflight error: {exc}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
