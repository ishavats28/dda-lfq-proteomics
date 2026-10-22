#!/usr/bin/env python3
"""Guard future biological differential analysis against invalid designs."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", required=True, type=Path)
    parser.add_argument("--replicate-type", choices=("biological", "technical"), required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        with args.design.resolve(strict=True).open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        if args.replicate_type == "technical":
            raise ValueError("technical repeat measurements cannot be used as independent biological replicates")
        conditions = Counter((row.get("condition") or "").strip() for row in rows)
        conditions.pop("", None)
        if len(conditions) < 2:
            raise ValueError("biological differential analysis requires at least two conditions")
        deficient = sorted(condition for condition, count in conditions.items() if count < 2)
        if deficient:
            raise ValueError("each condition requires at least two biological replicates: " + ", ".join(deficient))
        subjects = [(row.get("subject") or "").strip() for row in rows]
        populated = [subject for subject in subjects if subject]
        if populated and len(populated) != len(set(populated)):
            raise ValueError("duplicate biological subject cannot be presented as an independent sample")
        if args.output:
            args.output.write_text(
                "status\tok\nconditions\t" + str(len(conditions)) + "\nminimum_replicates\t" + str(min(conditions.values())) + "\n",
                encoding="utf-8",
            )
    except (OSError, UnicodeError, ValueError, csv.Error) as exc:
        print(f"differential-design validation error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
