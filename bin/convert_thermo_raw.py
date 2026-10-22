#!/usr/bin/env python3
"""Run a verified ProteoWizard msconvert Thermo RAW to mzML conversion."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path


SAMPLE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
VERSION_PATTERN = re.compile(
    r"ProteoWizard[^\r\n]*?(?:release|version)?\s*[:=]?\s*(\d+(?:\.\d+){2,}(?:\.\d+)*)",
    re.IGNORECASE,
)
REQUIRED_HELP_OPTIONS = ("--mzML", "--filter", "--outdir", "--outfile")
PEAK_PICKING_FILTER = "peakPicking vendor msLevel=1-"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fail(message: str) -> int:
    print(f"RAW conversion error: {message}", file=sys.stderr)
    return 2


def windows_argument_path(path: Path) -> str:
    """Translate a WSL path for a Windows-native msconvert executable."""
    converted = subprocess.run(
        ["wslpath", "-w", str(path)],
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if converted.returncode != 0 or not converted.stdout.strip():
        detail = converted.stderr.strip() or f"exit status {converted.returncode}"
        raise OSError(f"could not translate WSL path for msconvert: {detail}")
    return converted.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", required=True)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--msconvert", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--provenance", required=True, type=Path)
    parser.add_argument("--stdout-log", required=True, type=Path)
    parser.add_argument("--stderr-log", required=True, type=Path)
    args = parser.parse_args()

    try:
        raw = args.input.absolute()
        tool = args.msconvert.absolute()
        if not SAMPLE_PATTERN.fullmatch(args.sample):
            return fail(f"sample '{args.sample}' is not filesystem-safe")
        if raw.suffix.lower() != ".raw":
            return fail(f"input must have a .raw extension: {raw.name}")
        if not raw.exists():
            return fail(f"RAW file does not exist: {raw}")
        if not raw.is_file() or not os.access(raw, os.R_OK):
            return fail(f"RAW input is not a readable regular file: {raw}")
        if not tool.exists():
            return fail(f"msconvert executable does not exist: {tool}")
        if not tool.is_file() or not os.access(tool, os.X_OK):
            return fail(f"msconvert path is not an executable regular file: {tool}")

        help_result = subprocess.run(
            [str(tool), "--help"], text=True, capture_output=True, check=False, timeout=60
        )
        help_text = help_result.stdout + help_result.stderr
        if help_result.returncode != 0:
            return fail(f"msconvert --help exited with status {help_result.returncode}")
        missing = [option for option in REQUIRED_HELP_OPTIONS if option not in help_text]
        if missing:
            return fail("msconvert help is missing required options: " + ", ".join(missing))
        version_match = VERSION_PATTERN.search(help_text)
        if not version_match:
            return fail("could not determine the ProteoWizard version from msconvert --help")
        version = version_match.group(1)

        args.output_dir.mkdir(parents=True, exist_ok=True)
        output_dir = args.output_dir.resolve()
        output = output_dir / f"{args.sample}.mzML"
        windows_tool = sys.platform.startswith("linux") and tool.suffix.lower() == ".exe"
        # Resolve staged Nextflow symlinks before handing a path to a Windows process.
        command_raw = windows_argument_path(raw.resolve()) if windows_tool else str(raw)
        command_output_dir = (
            windows_argument_path(output_dir) if windows_tool else str(output_dir)
        )
        command = [
            str(tool),
            "--mzML",
            "--filter",
            PEAK_PICKING_FILTER,
            "--outdir",
            command_output_dir,
            "--outfile",
            output.name,
            command_raw,
        ]
        started = time.perf_counter()
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        elapsed = time.perf_counter() - started
        args.stdout_log.write_text(completed.stdout, encoding="utf-8")
        args.stderr_log.write_text(completed.stderr, encoding="utf-8")
        if completed.returncode != 0:
            return fail(f"msconvert exited with status {completed.returncode}; see conversion logs")
        if not output.exists() or not output.is_file() or output.stat().st_size == 0:
            return fail(f"msconvert did not produce a non-empty mzML file: {output.name}")

        display_command = [
            "msconvert",
            "--mzML",
            "--filter",
            PEAK_PICKING_FILTER,
            "--outdir",
            ".",
            "--outfile",
            output.name,
            raw.name,
        ]
        fields = [
            ("field", "value"),
            ("proteowizard_version", version),
            ("input_filename", raw.name),
            ("input_bytes", str(raw.stat().st_size)),
            ("input_sha256", sha256(raw)),
            ("output_filename", output.name),
            ("output_bytes", str(output.stat().st_size)),
            ("output_sha256", sha256(output)),
            ("peak_picking_filter", PEAK_PICKING_FILTER),
            ("conversion_seconds", f"{elapsed:.6f}"),
            ("command", shlex.join(display_command)),
        ]
        args.provenance.write_text(
            "".join(f"{key}\t{value}\n" for key, value in fields), encoding="utf-8"
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return fail(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
