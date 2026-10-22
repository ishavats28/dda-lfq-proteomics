#!/usr/bin/env python3
"""Stream an mzML file and write a compact pre-QC record."""

from __future__ import annotations

import argparse
import csv
import math
import sys
from importlib.metadata import version
from pathlib import Path

import pymzml


FIELDS = (
    "sample",
    "input_filename",
    "total_spectra",
    "ms1_spectra",
    "ms2_spectra",
    "minimum_retention_time_minutes",
    "maximum_retention_time_minutes",
    "precursor_information_observed_for_ms2",
    "spectra_with_nonempty_peak_arrays",
    "parsing_status",
)


def format_number(value: float | None) -> str:
    return "NA" if value is None else format(value, ".10g")


def inspect_mzml(sample: str, input_path: Path) -> dict[str, str | int]:
    total = 0
    ms1 = 0
    ms2 = 0
    peak_spectra = 0
    minimum_retention_time: float | None = None
    maximum_retention_time: float | None = None
    precursor_observed = False

    reader = pymzml.run.Reader(str(input_path), build_index_from_scratch=False)
    try:
        for spectrum in reader:
            total += 1
            level = spectrum.ms_level
            if level == 1:
                ms1 += 1
            elif level == 2:
                ms2 += 1
                if spectrum.selected_precursors:
                    precursor_observed = True

            try:
                retention_time = spectrum.scan_time_in_minutes()
            except (KeyError, TypeError, ValueError):
                retention_time = None
            if retention_time is not None and math.isfinite(float(retention_time)):
                retention_time = float(retention_time)
                if minimum_retention_time is None or retention_time < minimum_retention_time:
                    minimum_retention_time = retention_time
                if maximum_retention_time is None or retention_time > maximum_retention_time:
                    maximum_retention_time = retention_time

            peaks = spectrum.peaks("raw")
            if len(peaks) > 0:
                peak_spectra += 1
    finally:
        close = getattr(reader, "close", None)
        if callable(close):
            close()

    if total == 0:
        raise ValueError("file contains no spectra")

    precursor_value = "NA" if ms2 == 0 else str(precursor_observed).lower()
    return {
        "sample": sample,
        "input_filename": input_path.name,
        "total_spectra": total,
        "ms1_spectra": ms1,
        "ms2_spectra": ms2,
        "minimum_retention_time_minutes": format_number(minimum_retention_time),
        "maximum_retention_time_minutes": format_number(maximum_retention_time),
        "precursor_information_observed_for_ms2": precursor_value,
        "spectra_with_nonempty_peak_arrays": peak_spectra,
        "parsing_status": "ok",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", required=True)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-pymzml-version")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    installed_version = version("pymzML")
    if args.expected_pymzml_version and installed_version != args.expected_pymzml_version:
        print(
            f"mzML QC error for sample '{args.sample}' file '{args.input}': "
            f"expected pymzML {args.expected_pymzml_version}, found {installed_version}",
            file=sys.stderr,
        )
        return 2

    temporary = args.output.with_name(args.output.name + ".tmp")
    try:
        result = inspect_mzml(args.sample, args.input)
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerow(result)
        temporary.replace(args.output)
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        print(
            f"mzML QC error for sample '{args.sample}' file '{args.input}': {exc}",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
