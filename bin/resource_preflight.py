#!/usr/bin/env python3
"""Check Linux memory and filesystem capacity before a scientific search."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def memory_values() -> dict[str, int]:
    wanted = {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}
    values: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        name = line.split(":", 1)[0]
        if name in wanted:
            values[name] = int(line.split()[1]) * 1024
    missing = sorted(wanted - values.keys())
    if missing:
        raise RuntimeError(f"missing /proc/meminfo field(s): {', '.join(missing)}")
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minimum-gib", type=float, help="Deprecated alias for --minimum-available-gib")
    parser.add_argument("--minimum-total-gib", type=float, default=0)
    parser.add_argument("--minimum-available-gib", type=float)
    parser.add_argument("--minimum-free-disk-gib", type=float, default=0)
    parser.add_argument("--path", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    minimum_available_gib = args.minimum_available_gib
    if minimum_available_gib is None:
        minimum_available_gib = args.minimum_gib
    if minimum_available_gib is None:
        parser.error("--minimum-available-gib is required")

    memory = memory_values()
    disk = shutil.disk_usage(args.path.resolve())
    thresholds = {
        "mem_total_bytes": int(args.minimum_total_gib * 1024**3),
        "mem_available_bytes": int(minimum_available_gib * 1024**3),
        "disk_free_bytes": int(args.minimum_free_disk_gib * 1024**3),
    }
    observed = {
        "mem_total_bytes": memory["MemTotal"],
        "mem_available_bytes": memory["MemAvailable"],
        "swap_total_bytes": memory["SwapTotal"],
        "swap_free_bytes": memory["SwapFree"],
        "disk_free_bytes": disk.free,
    }
    failures = [name for name, minimum in thresholds.items() if observed[name] < minimum]
    status = "fail" if failures else "pass"
    args.output.write_text(
        "metric\tvalue\n"
        + "".join(f"{name}\t{value}\n" for name, value in observed.items())
        + "".join(f"minimum_{name}\t{value}\n" for name, value in thresholds.items())
        + f"status\t{status}\n",
        encoding="utf-8",
    )
    if failures:
        details = "; ".join(
            f"{name} is {observed[name] / 1024**3:.2f} GiB, requires {thresholds[name] / 1024**3:.2f} GiB"
            for name in failures
        )
        print(
            f"resource preflight error: {details}",
            file=sys.stderr,
        )
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
