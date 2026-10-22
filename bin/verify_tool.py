#!/usr/bin/env python3
"""Verify configured scientific executables and emit concise version errors."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path


def regular_readable(path: Path, label: str) -> Path:
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError(f"{label} does not exist: {path}") from exc
    if not resolved.is_file():
        raise ValueError(f"{label} is not a regular file: {resolved}")
    if not os.access(resolved, os.R_OK):
        raise ValueError(f"{label} is not readable: {resolved}")
    return resolved


def verify_philosopher(path: Path, expected: str) -> str:
    executable = regular_readable(path, "Philosopher executable")
    completed = subprocess.run([str(executable), "version"], text=True, capture_output=True, timeout=30, check=False)
    combined = completed.stdout + completed.stderr
    if completed.returncode != 0:
        raise ValueError(f"Philosopher version command failed with exit code {completed.returncode}")
    match = re.search(r"version=v?([0-9]+(?:\.[0-9]+)+)", combined)
    if not match:
        raise ValueError("could not parse Philosopher version output")
    detected = match.group(1)
    if detected != expected:
        raise ValueError(f"expected Philosopher {expected}, detected {detected}")
    return detected


def verify_msfragger(path: Path, expected: str, java: str) -> str:
    jar = regular_readable(path, "MSFragger JAR")
    if not zipfile.is_zipfile(jar):
        raise ValueError(f"MSFragger JAR is not a valid JAR/ZIP file: {jar}")
    completed = subprocess.run(
        [java, "-Xmx512m", "-jar", str(jar), "--help"],
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    combined = completed.stdout + completed.stderr
    match = re.search(r"MSFragger[^\r\n]*?([0-9]+\.[0-9]+(?:\.[0-9]+)?)", combined, re.IGNORECASE)
    if not match:
        raise ValueError(f"could not parse MSFragger version output; command exit code {completed.returncode}")
    detected = match.group(1)
    if detected != expected:
        raise ValueError(f"expected MSFragger {expected}, detected {detected}")
    return detected


def verify_ionquant(path: Path, expected: str, java: str) -> str:
    jar = regular_readable(path, "IonQuant JAR")
    if not zipfile.is_zipfile(jar):
        raise ValueError(f"IonQuant JAR is not a valid JAR/ZIP file: {jar}")
    completed = subprocess.run(
        [java, "-Xmx512m", "-jar", str(jar), "--help"],
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    combined = completed.stdout + completed.stderr
    match = re.search(r"IonQuant[^\r\n]*?([0-9]+\.[0-9]+(?:\.[0-9]+)?)", combined, re.IGNORECASE)
    if not match:
        raise ValueError(f"could not parse IonQuant version output; command exit code {completed.returncode}")
    detected = match.group(1)
    if detected != expected:
        raise ValueError(f"expected IonQuant {expected}, detected {detected}")
    return detected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", choices=("philosopher", "msfragger", "ionquant"), required=True)
    parser.add_argument("--path", required=True, type=Path)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--java", default="java")
    args = parser.parse_args()
    try:
        if args.tool == "philosopher":
            detected = verify_philosopher(args.path, args.expected_version)
        elif args.tool == "msfragger":
            detected = verify_msfragger(args.path, args.expected_version, args.java)
        else:
            detected = verify_ionquant(args.path, args.expected_version, args.java)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"tool validation error: {exc}", file=sys.stderr)
        return 2
    print(f"{args.tool}\t{detected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
