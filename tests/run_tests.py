#!/usr/bin/env python3
"""Lightweight deterministic tests for workflow input and analysis contracts."""

from __future__ import annotations

import csv
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
FIXTURES = PROJECT / "tests" / "fixtures"
VALIDATOR = PROJECT / "bin" / "validate_samplesheet.py"
QC = PROJECT / "bin" / "mzml_qc.py"
FASTA_VALIDATOR = PROJECT / "bin" / "validate_fasta.py"
TOOL_VALIDATOR = PROJECT / "bin" / "verify_tool.py"
PARAMETER_MATERIALIZER = PROJECT / "bin" / "materialize_msfragger_params.py"
RESOURCE_PREFLIGHT = PROJECT / "bin" / "resource_preflight.py"
DATABASE_CACHE = PROJECT / "bin" / "database_cache.py"
IDENTIFICATION_SUMMARY = PROJECT / "bin" / "summarize_identifications.py"
DOWNLOAD_PREFLIGHT = PROJECT / "bin" / "download_preflight.py"
RAW_CONVERTER = PROJECT / "bin" / "convert_thermo_raw.py"
IONQUANT_EXT_VALIDATOR = PROJECT / "bin" / "validate_ionquant_ext.py"
QUANT_MANIFEST_VALIDATOR = PROJECT / "bin" / "validate_quant_manifest.py"
QUANT_SUMMARY = PROJECT / "bin" / "summarize_quantification.py"
DESIGN_VALIDATOR = PROJECT / "bin" / "validate_design.py"
DIFFERENTIAL_DESIGN_VALIDATOR = PROJECT / "bin" / "validate_differential_design.py"
MATRIX_BUILDER = PROJECT / "bin" / "build_protein_matrix.py"
MATRIX_QC = PROJECT / "bin" / "quant_qc.py"
EXPLORATORY_QC = PROJECT / "bin" / "exploratory_analysis.py"
REPORT_GENERATOR = PROJECT / "bin" / "generate_report.py"
SEARCH_FIXTURES = FIXTURES / "search"
FASTA_INVALID = FIXTURES / "fasta_invalid"


class ContractTests(unittest.TestCase):
    def run_validator(self, fixture: str, output: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
                "--input",
                str(FIXTURES / fixture),
                "--base-dir",
                str(FIXTURES),
                "--output",
                str(output),
            ],
            text=True,
            capture_output=True,
            check=False,
        )

    def assert_invalid(self, fixture: str, expected: str) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "normalized.tsv"
            completed = self.run_validator(fixture, output)
            self.assertEqual(completed.returncode, 2, completed.stderr)
            self.assertIn(expected, completed.stderr)
            self.assertFalse(output.exists())

    def test_valid_sample_sheet_is_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "normalized.tsv"
            completed = self.run_validator("valid_samplesheet.tsv", output)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            with output.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["sample"], "synthetic_01")
            self.assertEqual(rows[0]["replicate"], "1")
            self.assertEqual(Path(rows[0]["mzml"]), (FIXTURES / "tiny_valid.mzML").resolve())
            self.assertEqual(list(rows[0]), ["sample", "condition", "replicate", "mzml", "batch", "fraction"])

    def test_missing_required_column_is_rejected(self) -> None:
        self.assert_invalid("invalid_missing_column.tsv", "missing required column(s): replicate")

    def test_duplicate_sample_is_rejected(self) -> None:
        self.assert_invalid("invalid_duplicate_sample.tsv", "duplicate sample ID")

    def test_nonpositive_replicate_is_rejected(self) -> None:
        self.assert_invalid("invalid_nonpositive_replicate.tsv", "replicate must be a positive integer")

    def test_missing_mzml_is_rejected(self) -> None:
        self.assert_invalid("invalid_missing_mzml.tsv", "mzML file does not exist")

    def test_wrong_extension_is_rejected(self) -> None:
        self.assert_invalid("invalid_wrong_extension.tsv", "mzML path must end in .mzML")

    def test_duplicate_resolved_path_is_rejected(self) -> None:
        self.assert_invalid("invalid_duplicate_path.tsv", "duplicate resolved mzML path")

    def test_valid_mzml_qc_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "qc.tsv"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(QC),
                    "--sample",
                    "synthetic_01",
                    "--input",
                    str(FIXTURES / "tiny_valid.mzML"),
                    "--output",
                    str(output),
                    "--expected-pymzml-version",
                    "2.7.0",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            with output.open(encoding="utf-8", newline="") as handle:
                row = next(csv.DictReader(handle, delimiter="\t"))
            self.assertEqual(row["total_spectra"], "2")
            self.assertEqual(row["ms1_spectra"], "1")
            self.assertEqual(row["ms2_spectra"], "1")
            self.assertEqual(row["minimum_retention_time_minutes"], "1")
            self.assertEqual(row["maximum_retention_time_minutes"], "2")
            self.assertEqual(row["precursor_information_observed_for_ms2"], "true")
            self.assertEqual(row["spectra_with_nonempty_peak_arrays"], "2")
            self.assertEqual(row["parsing_status"], "ok")

    def test_malformed_mzml_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "qc.tsv"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(QC),
                    "--sample",
                    "malformed_01",
                    "--input",
                    str(FIXTURES / "malformed.mzML"),
                    "--output",
                    str(output),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 2, completed.stderr)
            self.assertIn("mzML QC error for sample 'malformed_01'", completed.stderr)
            self.assertFalse(output.exists())


class RawConversionTests(unittest.TestCase):
    def make_fake_msconvert(self, root: Path, executable: bool = True) -> Path:
        tool = root / "msconvert"
        tool.write_text(
            "#!/usr/bin/env python3\n"
            "import os, shutil, sys\n"
            "from pathlib import Path\n"
            "if '--help' in sys.argv:\n"
            "    print('ProteoWizard release: 3.0.999.0')\n"
            "    print('--mzML --filter --outdir --outfile')\n"
            "    raise SystemExit(0)\n"
            "mode = os.environ.get('FAKE_MSCONVERT_MODE', 'success')\n"
            "if mode == 'fail':\n"
            "    print('simulated conversion failure', file=sys.stderr)\n"
            "    raise SystemExit(9)\n"
            "outdir = Path(sys.argv[sys.argv.index('--outdir') + 1])\n"
            "outfile = sys.argv[sys.argv.index('--outfile') + 1]\n"
            "output = outdir / outfile\n"
            "if mode == 'empty':\n"
            "    output.touch()\n"
            "else:\n"
            "    shutil.copyfile(os.environ['FAKE_MZML_SOURCE'], output)\n",
            encoding="utf-8",
        )
        tool.chmod(0o755 if executable else 0o644)
        return tool

    def run_conversion(
        self, root: Path, raw: Path, tool: Path, mode: str = "success"
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["FAKE_MSCONVERT_MODE"] = mode
        environment["FAKE_MZML_SOURCE"] = str(FIXTURES / "tiny_valid.mzML")
        return subprocess.run(
            [sys.executable, str(RAW_CONVERTER), "--sample", "yeast_test",
             "--input", str(raw), "--msconvert", str(tool), "--output-dir", str(root),
             "--provenance", str(root / "conversion.tsv"),
             "--stdout-log", str(root / "stdout.log"),
             "--stderr-log", str(root / "stderr.log")],
            text=True, capture_output=True, check=False, env=environment,
        )

    def test_missing_msconvert_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = root / "input.raw"
            raw.write_bytes(b"synthetic contract input")
            completed = self.run_conversion(root, raw, root / "missing-msconvert")
            self.assertEqual(completed.returncode, 2)
            self.assertIn("msconvert executable does not exist", completed.stderr)

    def test_nonexecutable_msconvert_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = root / "input.raw"
            raw.write_bytes(b"synthetic contract input")
            completed = self.run_conversion(root, raw, self.make_fake_msconvert(root, False))
            self.assertEqual(completed.returncode, 2)
            self.assertIn("not an executable regular file", completed.stderr)

    def test_wrong_raw_extension_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = root / "input.mzML"
            raw.write_bytes(b"not RAW")
            completed = self.run_conversion(root, raw, self.make_fake_msconvert(root))
            self.assertEqual(completed.returncode, 2)
            self.assertIn("input must have a .raw extension", completed.stderr)

    def test_failed_and_empty_conversions_are_rejected(self) -> None:
        for mode, message in (("fail", "exited with status 9"), ("empty", "non-empty mzML")):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                raw = root / "input.raw"
                raw.write_bytes(b"synthetic contract input")
                completed = self.run_conversion(root, raw, self.make_fake_msconvert(root), mode)
                self.assertEqual(completed.returncode, 2)
                self.assertIn(message, completed.stderr)

    def test_successful_conversion_hands_mzml_to_qc(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = root / "input.raw"
            raw.write_bytes(b"synthetic contract input")
            completed = self.run_conversion(root, raw, self.make_fake_msconvert(root))
            self.assertEqual(completed.returncode, 0, completed.stderr)
            mzml = root / "yeast_test.mzML"
            self.assertGreater(mzml.stat().st_size, 0)
            qc = root / "qc.tsv"
            checked = subprocess.run(
                [sys.executable, str(QC), "--sample", "yeast_test", "--input", str(mzml),
                 "--output", str(qc), "--expected-pymzml-version", "2.7.0"],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(checked.returncode, 0, checked.stderr)
            with qc.open(encoding="utf-8", newline="") as handle:
                row = next(csv.DictReader(handle, delimiter="\t"))
            self.assertEqual(row["parsing_status"], "ok")
            self.assertEqual(row["total_spectra"], "2")
            provenance = (root / "conversion.tsv").read_text(encoding="utf-8")
            self.assertIn("proteowizard_version\t3.0.999.0", provenance)
            self.assertIn("peakPicking vendor msLevel=1-", provenance)


class FastaContractTests(unittest.TestCase):
    def run_validator(self, source: Path, output: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(FASTA_VALIDATOR), "--input", str(source), "--output", str(output)],
            text=True,
            capture_output=True,
            check=False,
        )

    def assert_invalid(self, source: Path, expected: str) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "manifest.tsv"
            completed = self.run_validator(source, output)
            self.assertEqual(completed.returncode, 2, completed.stderr)
            self.assertIn(expected, completed.stderr)
            self.assertFalse(output.exists())

    def test_valid_fasta_manifest_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first.tsv"
            second = Path(temporary) / "second.tsv"
            source = SEARCH_FIXTURES / "synthetic_proteins.fasta"
            self.assertEqual(self.run_validator(source, first).returncode, 0)
            self.assertEqual(self.run_validator(source, second).returncode, 0)
            with first.open(encoding="utf-8", newline="") as handle:
                record = next(csv.DictReader(handle, delimiter="\t"))
            self.assertEqual(record["record_count"], "6")
            self.assertEqual(record["total_amino_acids"], "96")
            self.assertEqual(len(record["sha256"]), 64)
            self.assertEqual(record["validation_status"], "ok")
            self.assertEqual(first.read_text(encoding="utf-8"), second.read_text(encoding="utf-8"))

    def test_missing_fasta_is_rejected(self) -> None:
        self.assert_invalid(FASTA_INVALID / "missing.fasta", "FASTA file does not exist")

    def test_empty_fasta_is_rejected(self) -> None:
        self.assert_invalid(FASTA_INVALID / "empty.fasta", "FASTA file is empty")

    def test_sequence_before_header_is_rejected(self) -> None:
        self.assert_invalid(FASTA_INVALID / "sequence_before_header.fasta", "before the first FASTA header")

    def test_empty_sequence_is_rejected(self) -> None:
        self.assert_invalid(FASTA_INVALID / "empty_sequence.fasta", "has an empty sequence")

    def test_duplicate_identifier_is_rejected(self) -> None:
        self.assert_invalid(FASTA_INVALID / "duplicate_identifier.fasta", "duplicate FASTA identifier")

    def test_invalid_protein_character_is_rejected(self) -> None:
        self.assert_invalid(FASTA_INVALID / "invalid_characters.fasta", "invalid protein sequence character")

    def test_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(suffix=".fasta") as directory:
            self.assert_invalid(Path(directory), "not a regular file")


class ScientificToolContractTests(unittest.TestCase):
    def test_missing_tool_path_is_rejected(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(TOOL_VALIDATOR), "--tool", "philosopher", "--path", "missing-philosopher", "--expected-version", "5.1.0"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("does not exist", completed.stderr)

    def test_incorrect_philosopher_version_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fake = Path(temporary) / "philosopher"
            fake.write_text("#!/bin/sh\necho 'level=info version=v9.9.9'\n", encoding="utf-8")
            fake.chmod(0o755)
            completed = subprocess.run(
                [sys.executable, str(TOOL_VALIDATOR), "--tool", "philosopher", "--path", str(fake), "--expected-version", "5.1.0"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("expected Philosopher 5.1.0, detected 9.9.9", completed.stderr)

    def test_installed_philosopher_version(self) -> None:
        configured = os.environ.get("PHILOSOPHER_BIN")
        if not configured:
            self.skipTest("PHILOSOPHER_BIN is not configured")
        completed = subprocess.run(
            [sys.executable, str(TOOL_VALIDATOR), "--tool", "philosopher", "--path", configured, "--expected-version", "5.1.0"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("philosopher\t5.1.0", completed.stdout)

    def test_installed_msfragger_version(self) -> None:
        configured = os.environ.get("MSFRAGGER_JAR")
        if not configured:
            self.skipTest("MSFRAGGER_JAR is not configured; licensed-tool test not run")
        completed = subprocess.run(
            [sys.executable, str(TOOL_VALIDATOR), "--tool", "msfragger", "--path", configured, "--expected-version", "4.4.1"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("msfragger\t4.4.1", completed.stdout)

    def test_parameter_template_materialization_and_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "search.params"
            completed = subprocess.run(
                [sys.executable, str(PARAMETER_MATERIALIZER), "--template", str(PROJECT / "conf/msfragger/synthetic-search.params"), "--database", str(SEARCH_FIXTURES / "synthetic_proteins.fasta"), "--output", str(output)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            materialized = output.read_text(encoding="utf-8")
            self.assertNotIn("__DATABASE_NAME__", materialized)
            self.assertIn("database_name = ", materialized)

            invalid_template = Path(temporary) / "invalid.params"
            invalid_template.write_text("num_threads = 2\n", encoding="utf-8")
            failed = subprocess.run(
                [sys.executable, str(PARAMETER_MATERIALIZER), "--template", str(invalid_template), "--database", str(SEARCH_FIXTURES / "synthetic_proteins.fasta"), "--output", str(output)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(failed.returncode, 2)
            self.assertIn("exactly once; found 0", failed.stderr)

    def test_parameter_materializer_ignores_placeholder_in_comments(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            template = root / "template.params"
            template.write_text(
                "# __DATABASE_NAME__ documents the runtime value\n"
                "database_name = __DATABASE_NAME__\n",
                encoding="utf-8",
            )
            output = root / "search.params"
            completed = subprocess.run(
                [sys.executable, str(PARAMETER_MATERIALIZER), "--template", str(template),
                 "--database", str(SEARCH_FIXTURES / "synthetic_proteins.fasta"), "--output", str(output)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            lines = output.read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines[0], "# __DATABASE_NAME__ documents the runtime value")
            self.assertNotIn("__DATABASE_NAME__", lines[1])

    def test_parameter_materializer_preserves_staged_symlink_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            staged = root / "staged.fasta"
            staged.symlink_to(SEARCH_FIXTURES / "synthetic_proteins.fasta")
            template = root / "template.params"
            template.write_text("database_name = __DATABASE_NAME__\n", encoding="utf-8")
            output = root / "search.params"
            completed = subprocess.run(
                [sys.executable, str(PARAMETER_MATERIALIZER), "--template", str(template),
                 "--database", str(staged), "--output", str(output)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(
                output.read_text(encoding="utf-8").strip(),
                f"database_name = {staged.absolute()}",
            )

    def test_constrained_profile_only_reduces_maximum_peptide_length(self) -> None:
        def active_settings(path: Path) -> dict[str, str]:
            settings: dict[str, str] = {}
            for raw_line in path.read_text(encoding="utf-8").splitlines():
                line = raw_line.split("#", 1)[0].strip()
                if not line or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                settings[key.strip()] = value.strip()
            return settings

        production = active_settings(PROJECT / "conf/msfragger/closed-search.params")
        constrained = active_settings(PROJECT / "conf/msfragger/constrained-validation.params")
        differences = {
            key: (production.get(key), constrained.get(key))
            for key in production.keys() | constrained.keys()
            if production.get(key) != constrained.get(key)
        }
        self.assertEqual(differences, {"digest_max_length": ("50", "35")})

    def test_resource_preflight_failure_is_clear(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "preflight.tsv"
            completed = subprocess.run(
                [sys.executable, str(RESOURCE_PREFLIGHT), "--minimum-gib", "1024", "--output", str(output)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 3)
            self.assertIn("resource preflight error", completed.stderr)
            self.assertIn("status\tfail", output.read_text(encoding="utf-8"))

    def test_incorrect_msfragger_version_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            jar = root / "MSFragger.jar"
            with zipfile.ZipFile(jar, "w") as archive:
                archive.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
            fake_java = root / "java"
            fake_java.write_text("#!/bin/sh\necho 'MSFragger version 9.9.9'\n", encoding="utf-8")
            fake_java.chmod(0o755)
            completed = subprocess.run(
                [sys.executable, str(TOOL_VALIDATOR), "--tool", "msfragger", "--path", str(jar), "--expected-version", "4.4.1", "--java", str(fake_java)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("expected MSFragger 4.4.1, detected 9.9.9", completed.stderr)


class DatabaseCacheTests(unittest.TestCase):
    def create_manifest(self, fasta: Path, manifest: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable, str(DATABASE_CACHE), "create", "--fasta", str(fasta),
                "--manifest", str(manifest), "--database-id", "test", "--source", "synthetic",
                "--source-accession", "none", "--taxonomy-id", "0", "--organism", "synthetic",
                "--review-status", "not-applicable", "--philosopher-version", "5.1.0",
                "--contaminants", "none", "--decoy-strategy", "precomputed-test-only",
                "--decoy-prefix", "rev_",
            ], text=True, capture_output=True, check=False,
        )

    def test_database_manifest_counts_and_cache_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fasta = root / "database.fasta"
            fasta.write_text(">target\nPEPTIDE\n>rev_target\nEDITPEP\n>contam_KERATIN\nPEPTIDE\n", encoding="utf-8")
            manifest = root / "database.manifest.tsv"
            self.assertEqual(self.create_manifest(fasta, manifest).returncode, 0)
            with manifest.open(encoding="utf-8", newline="") as handle:
                row = next(csv.DictReader(handle, delimiter="\t"))
            self.assertEqual((row["target_count"], row["decoy_count"], row["contaminant_count"]), ("2", "1", "1"))
            verified = subprocess.run(
                [sys.executable, str(DATABASE_CACHE), "verify", "--fasta", str(fasta), "--manifest", str(manifest)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(verified.returncode, 0, verified.stderr)

    def test_database_cache_checksum_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fasta = root / "database.fasta"
            fasta.write_text(">target\nPEPTIDE\n", encoding="utf-8")
            manifest = root / "database.manifest.tsv"
            self.assertEqual(self.create_manifest(fasta, manifest).returncode, 0)
            fasta.write_text(">target\nPEPTIDER\n", encoding="utf-8")
            failed = subprocess.run(
                [sys.executable, str(DATABASE_CACHE), "verify", "--fasta", str(fasta), "--manifest", str(manifest)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(failed.returncode, 2)
            self.assertIn("checksum mismatch", failed.stderr)


class DownloadSafetyTests(unittest.TestCase):
    def test_small_file_passes_download_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "preflight.tsv"
            completed = subprocess.run(
                [sys.executable, str(DOWNLOAD_PREFLIGHT), "--remote-bytes", "1048576", "--path", str(PROJECT), "--output", str(output)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("status\tpass", output.read_text(encoding="utf-8"))

    def test_file_over_four_gib_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "preflight.tsv"
            completed = subprocess.run(
                [sys.executable, str(DOWNLOAD_PREFLIGHT), "--remote-bytes", str(4 * 1024**3 + 1), "--path", temporary, "--output", str(output)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(completed.returncode, 3)
            self.assertIn("exceeds the 4 GiB", completed.stderr)


class IdentificationSummaryTests(unittest.TestCase):
    def test_identification_summary_uses_reported_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            qc = root / "qc.tsv"
            qc.write_text("sample\ttotal_spectra\tms2_spectra\nrun\t10\t8\n", encoding="utf-8")
            pepxml = root / "raw.pepXML"
            pepxml.write_text("<msms_pipeline_analysis>\n<spectrum_query spectrum=\"a\">\n</spectrum_query>\n</msms_pipeline_analysis>\n", encoding="utf-8")
            psm = root / "psm.tsv"
            psm.write_text("Spectrum\tProtein\na\tsp|P1|TARGET\nb\trev_sp|P2|DECOY\n", encoding="utf-8")
            peptide = root / "peptide.tsv"
            peptide.write_text("Peptide\nPEPTIDE\n", encoding="utf-8")
            protein = root / "protein.tsv"
            protein.write_text("Protein\nsp|P1|TARGET\n", encoding="utf-8")
            manifest = root / "fasta.validation.tsv"
            manifest.write_text("filename\tresolved_path\trecord_count\ttotal_amino_acids\tsha256\tvalidation_status\ndb.fasta\t/path\t2\t14\t" + "a" * 64 + "\tok\n", encoding="utf-8")
            output = root / "summary.tsv"
            completed = subprocess.run(
                [sys.executable, str(IDENTIFICATION_SUMMARY), "--sample", "run", "--mzml-qc", str(qc),
                 "--raw-pepxml", str(pepxml), "--psm", str(psm), "--peptide", str(peptide),
                 "--protein", str(protein), "--database-manifest", str(manifest), "--output", str(output)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            with output.open(encoding="utf-8", newline="") as handle:
                row = next(csv.DictReader(handle, delimiter="\t"))
            self.assertEqual(row["raw_msfragger_psms"], "1")
            self.assertEqual(row["filtered_psms"], "2")
            self.assertEqual(row["target_psms"], "1")
            self.assertEqual(row["decoy_psms"], "1")

    def test_empty_raw_pepxml_fails_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("qc.tsv", "psm.tsv", "peptide.tsv", "protein.tsv", "manifest.tsv"):
                (root / name).write_text("header\n", encoding="utf-8")
            raw = root / "raw.pepXML"
            raw.write_text("<msms_pipeline_analysis/>\n", encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(IDENTIFICATION_SUMMARY), "--sample", "run", "--mzml-qc", str(root / "qc.tsv"),
                 "--raw-pepxml", str(raw), "--psm", str(root / "psm.tsv"), "--peptide", str(root / "peptide.tsv"),
                 "--protein", str(root / "protein.tsv"), "--database-manifest", str(root / "manifest.tsv"),
                 "--output", str(root / "summary.tsv")], text=True, capture_output=True, check=False,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertFalse((root / "summary.tsv").exists())


class IonQuantContractTests(unittest.TestCase):
    def write_psm(self, path: Path, include_row: bool = True) -> None:
        text = "Spectrum\tPeptide\tProtein\tPeptideProphet Probability\n"
        if include_row:
            text += "run.1.1.2\tPEPTIDE\tsp|P1|TEST\t0.99\n"
        path.write_text(text, encoding="utf-8")

    def test_missing_ionquant_jar_is_rejected(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(TOOL_VALIDATOR), "--tool", "ionquant", "--path", "missing-ionquant.jar",
             "--expected-version", "1.11.20"], text=True, capture_output=True, check=False,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("IonQuant JAR does not exist", completed.stderr)

    def test_wrong_ionquant_version_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            jar = root / "IonQuant.jar"
            with zipfile.ZipFile(jar, "w") as archive:
                archive.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
            java = root / "java"
            java.write_text("#!/bin/sh\necho 'IonQuant version IonQuant-9.9.9'\nexit 1\n", encoding="utf-8")
            java.chmod(0o755)
            completed = subprocess.run(
                [sys.executable, str(TOOL_VALIDATOR), "--tool", "ionquant", "--path", str(jar),
                 "--expected-version", "1.11.20", "--java", str(java)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("expected IonQuant 1.11.20, detected 9.9.9", completed.stderr)

    def test_installed_ionquant_version(self) -> None:
        jar = os.environ.get("IONQUANT_JAR")
        if not jar:
            self.skipTest("IONQUANT_JAR is not configured")
        completed = subprocess.run(
            [sys.executable, str(TOOL_VALIDATOR), "--tool", "ionquant", "--path", jar,
             "--expected-version", "1.11.20"], text=True, capture_output=True, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_missing_and_incomplete_ext_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for ext, message in ((root / "missing", "does not exist"), (root, "must contain exactly one")):
                with self.subTest(message=message):
                    completed = subprocess.run(
                        [sys.executable, str(IONQUANT_EXT_VALIDATOR), "--ext", str(ext),
                         "--output", str(root / "ext.tsv")], text=True, capture_output=True, check=False,
                    )
                    self.assertEqual(completed.returncode, 2)
                    self.assertIn(message, completed.stderr)

    def test_valid_ext_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "libtimsdata-2-21-0-4.so").write_bytes(b"test-only native resource")
            output = root / "ext.tsv"
            completed = subprocess.run(
                [sys.executable, str(IONQUANT_EXT_VALIDATOR), "--ext", str(root), "--output", str(output)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("validation_status\tok", output.read_text(encoding="utf-8"))

    def test_quant_manifest_rejects_missing_spectral_and_psm_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cases = (
                ("run\tmissing.mzML\tpsm.tsv\tprotein.tsv\n", "mzML does not exist"),
                ("run\ttiny.mzML\tmissing/psm.tsv\tprotein.tsv\n", "psm.tsv does not exist"),
                ("run\ttiny.mzML\tpsm.tsv\tmissing/protein.tsv\n", "protein.tsv does not exist"),
            )
            (root / "tiny.mzML").write_bytes((FIXTURES / "tiny_valid.mzML").read_bytes())
            self.write_psm(root / "psm.tsv")
            (root / "protein.tsv").write_text("Protein\tTotal Intensity\nP1\t1\n", encoding="utf-8")
            for body, message in cases:
                with self.subTest(message=message):
                    manifest = root / "manifest.tsv"
                    manifest.write_text("sample\tmzml\tpsm\tprotein\n" + body, encoding="utf-8")
                    completed = subprocess.run(
                        [sys.executable, str(QUANT_MANIFEST_VALIDATOR), "--input", str(manifest),
                         "--base-dir", str(root), "--output", str(root / "normalized.tsv")],
                        text=True, capture_output=True, check=False,
                    )
                    self.assertEqual(completed.returncode, 2)
                    self.assertIn(message, completed.stderr)

    def test_quant_manifest_rejects_empty_psm_and_malformed_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "tiny.mzML").write_bytes((FIXTURES / "tiny_valid.mzML").read_bytes())
            (root / "psm.tsv").write_text("", encoding="utf-8")
            (root / "protein.tsv").write_text("Protein\tTotal Intensity\nP1\t1\n", encoding="utf-8")
            manifest = root / "manifest.tsv"
            manifest.write_text("sample\tmzml\tpsm\tprotein\nrun\ttiny.mzML\tpsm.tsv\tprotein.tsv\n", encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(QUANT_MANIFEST_VALIDATOR), "--input", str(manifest),
                 "--base-dir", str(root), "--output", str(root / "normalized.tsv")],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("psm.tsv is empty", completed.stderr)
            self.write_psm(root / "psm.tsv")
            manifest.write_text("sample\tmzml\tpsm\tprotein\nrun\ttiny.mzML\tpsm.tsv\tprotein.tsv\textra\n", encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(QUANT_MANIFEST_VALIDATOR), "--input", str(manifest),
                 "--base-dir", str(root), "--output", str(root / "normalized.tsv")],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("too many tab-separated fields", completed.stderr)

    def test_quant_summary_and_missing_output_guard(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, content in (
                ("ion.tsv", "Ion\tIntensity\ni1\t10\ni2\t20\n"),
                ("peptide.tsv", "Peptide\tIntensity\nPEP\t15\n"),
                ("protein.tsv", "Protein\tIntensity run\tMaxLFQ Intensity run\nP1\t30\t25\nP2\t0\t0\n"),
            ):
                (root / name).write_text(content, encoding="utf-8")
            output = root / "summary.tsv"
            completed = subprocess.run(
                [sys.executable, str(QUANT_SUMMARY), "--reports", str(root), "--output", str(output),
                 "--mbr", "off"], text=True, capture_output=True, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            summary = output.read_text(encoding="utf-8")
            self.assertIn("quantified_ions\t2", summary)
            self.assertIn("maxlfq_proteins\t1", summary)
            (root / "ion.tsv").unlink()
            completed = subprocess.run(
                [sys.executable, str(QUANT_SUMMARY), "--reports", str(root),
                 "--output", str(root / "failed.tsv"), "--mbr", "off"],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("missing non-empty IonQuant report", completed.stderr)

    def test_quant_summary_uses_combined_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root / "runs" / "run1"
            combined = root / "combined"
            run.mkdir(parents=True)
            combined.mkdir()
            for name, content in (
                ("ion.tsv", "Ion\tIntensity\ni1\t10\n"),
                ("peptide.tsv", "Peptide\tIntensity\nPEP\t10\n"),
                ("protein.tsv", "Protein\tTotal Intensity\nP1\t10\n"),
            ):
                (run / name).write_text(content, encoding="utf-8")
            (combined / "combined_ion.tsv").write_text("Ion\trun1 Intensity\ni1\t10\ni2\t20\n", encoding="utf-8")
            (combined / "combined_peptide.tsv").write_text("Peptide\trun1 Intensity\nA\t10\nB\t20\n", encoding="utf-8")
            (combined / "combined_protein.tsv").write_text(
                "Protein\trun1 Intensity\trun2 Intensity\trun1 MaxLFQ Intensity\trun2 MaxLFQ Intensity\n"
                "P1\t10\t20\t11\t19\nP2\t5\t0\t5\t0\n", encoding="utf-8",
            )
            output = root / "summary.tsv"
            completed = subprocess.run(
                [sys.executable, str(QUANT_SUMMARY), "--reports", str(root), "--output", str(output),
                 "--mbr", "off"], text=True, capture_output=True, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            summary = output.read_text(encoding="utf-8")
            self.assertIn("runs_processed\t2", summary)
            self.assertIn("quantified_proteins\t2", summary)
            self.assertIn("maxlfq_proteins\t2", summary)
            self.assertIn("proteins_quantified_across_all_runs\t1", summary)


class DownstreamAnalysisTests(unittest.TestCase):
    HEADER = (
        "Protein\tProtein ID\tGene\tDescription\tCombined Total Peptides\t"
        "S1 MaxLFQ Intensity\tS2 MaxLFQ Intensity\tS3 MaxLFQ Intensity\n"
    )

    def write_protein(self, path: Path, rows: str) -> None:
        path.write_text(self.HEADER + rows, encoding="utf-8")

    def run_matrix(self, root: Path, rows: str) -> subprocess.CompletedProcess[str]:
        protein = root / "combined_protein.tsv"
        self.write_protein(protein, rows)
        return subprocess.run(
            [sys.executable, str(MATRIX_BUILDER), "--protein", str(protein), "--outdir", str(root / "matrix")],
            text=True, capture_output=True, check=False,
        )

    def test_matrix_filtering_missingness_and_log2_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            completed = self.run_matrix(
                root,
                "P1\t1\tG1\tProtein 1\t3\t8\t0\t16\n"
                "P2\t2\tG2\tAll zero\t1\t0\t0\t0\n"
                "contam_P3\t3\t\tContaminant\t1\t5\t5\t5\n"
                "rev_P4\t4\t\tDecoy\t1\t6\t6\t6\n"
                "P5\t5\tG5\tProtein 5\t2\t4\t8\t16\n",
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            with (root / "matrix" / "protein_matrix.raw.tsv").open(encoding="utf-8", newline="") as handle:
                raw = list(csv.DictReader(handle, delimiter="\t"))
            with (root / "matrix" / "protein_matrix.log2.tsv").open(encoding="utf-8", newline="") as handle:
                log2 = list(csv.DictReader(handle, delimiter="\t"))
            self.assertEqual(list(raw[0]), ["protein", "S1", "S2", "S3"])
            self.assertEqual([row["protein"] for row in raw], ["P1", "P5"])
            self.assertEqual(raw[0]["S2"], "")
            self.assertEqual(float(log2[0]["S1"]), 3.0)
            summary = (root / "matrix" / "protein_matrix.summary.tsv").read_text(encoding="utf-8")
            for expected in ("decoy_rows_removed\t1", "contaminant_rows_removed\t1",
                             "unquantified_rows_removed\t1", "final_analytical_rows\t2"):
                self.assertIn(expected, summary)

    def test_matrix_rejects_duplicate_protein_groups(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            completed = self.run_matrix(
                root, "P1\t1\tG1\tOne\t1\t1\t2\t3\nP1\t1\tG1\tDuplicate\t1\t2\t3\t4\n"
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("duplicate protein identifier/group", completed.stderr)

    def test_design_contract_valid_and_invalid_cases(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            matrix = root / "matrix.tsv"
            matrix.write_text("protein\tS1\tS2\tS3\nP1\t1\t2\t3\n", encoding="utf-8")
            cases = (
                ("sample\tcondition\treplicate\nS1\tone\t1\nS2\tone\t2\nS3\tone\t3\n", 0, ""),
                ("sample\tcondition\treplicate\nS1\tone\t1\nS2\tone\t2\n", 2, "absent from complete design"),
                ("sample\tcondition\treplicate\nS1\tone\t1\nS1\tone\t2\nS3\tone\t3\n", 2, "duplicate sample"),
                ("sample\tcondition\treplicate\nS1\tone\t0\nS2\tone\t2\nS3\tone\t3\n", 2, "positive integer"),
                ("sample\tcondition\treplicate\nS1\tone\t1\nS2\tone\t2\nS4\tone\t3\n", 2, "absent from the quantitative matrix"),
            )
            for index, (content, code, message) in enumerate(cases):
                with self.subTest(index=index):
                    design = root / f"design-{index}.tsv"
                    design.write_text(content, encoding="utf-8")
                    completed = subprocess.run(
                        [sys.executable, str(DESIGN_VALIDATOR), "--design", str(design), "--matrix", str(matrix),
                         "--output", str(root / f"normalized-{index}.tsv")],
                        text=True, capture_output=True, check=False,
                    )
                    self.assertEqual(completed.returncode, code, completed.stderr)
                    if message:
                        self.assertIn(message, completed.stderr)

    def test_differential_design_guards(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            one = root / "one.tsv"
            one.write_text("sample\tcondition\treplicate\nS1\tone\t1\nS2\tone\t2\nS3\tone\t3\n", encoding="utf-8")
            technical = subprocess.run(
                [sys.executable, str(DIFFERENTIAL_DESIGN_VALIDATOR), "--design", str(one),
                 "--replicate-type", "technical"], text=True, capture_output=True, check=False,
            )
            self.assertEqual(technical.returncode, 2)
            self.assertIn("technical repeat measurements", technical.stderr)
            biological = subprocess.run(
                [sys.executable, str(DIFFERENTIAL_DESIGN_VALIDATOR), "--design", str(one),
                 "--replicate-type", "biological"], text=True, capture_output=True, check=False,
            )
            self.assertEqual(biological.returncode, 2)
            self.assertIn("at least two conditions", biological.stderr)
            deficient = root / "deficient.tsv"
            deficient.write_text(
                "sample\tcondition\treplicate\nS1\tA\t1\nS2\tA\t2\nS3\tB\t1\n", encoding="utf-8"
            )
            completed = subprocess.run(
                [sys.executable, str(DIFFERENTIAL_DESIGN_VALIDATOR), "--design", str(deficient),
                 "--replicate-type", "biological"], text=True, capture_output=True, check=False,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("at least two biological replicates", completed.stderr)

    def test_qc_pca_orientation_determinism_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            completed = self.run_matrix(
                root,
                "P1\t1\tG1\tOne\t3\t10\t11\t12\n"
                "P2\t2\tG2\tTwo\t3\t20\t22\t24\n"
                "P3\t3\tG3\tThree\t3\t30\t33\t36\n"
                "P4\t4\tG4\tMissing\t2\t40\t0\t44\n",
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            identification = root / "identification.tsv"
            identification.write_text(
                "sample\tfiltered_psms\tunique_peptides\tprotein_groups_or_proteins\n"
                "S1\t10\t8\t4\nS2\t11\t9\t4\nS3\t12\t10\t4\n", encoding="utf-8",
            )
            for suffix in ("a", "b"):
                quant = root / f"quant-{suffix}"
                exploratory = root / f"exploratory-{suffix}"
                q = subprocess.run(
                    [sys.executable, str(MATRIX_QC), "--raw-matrix", str(root / "matrix/protein_matrix.raw.tsv"),
                     "--log2-matrix", str(root / "matrix/protein_matrix.log2.tsv"),
                     "--identification-summary", str(identification), "--outdir", str(quant)],
                    text=True, capture_output=True, check=False,
                )
                self.assertEqual(q.returncode, 0, q.stderr)
                e = subprocess.run(
                    [sys.executable, str(EXPLORATORY_QC), "--raw-matrix", str(root / "matrix/protein_matrix.raw.tsv"),
                     "--log2-matrix", str(root / "matrix/protein_matrix.log2.tsv"), "--outdir", str(exploratory)],
                    text=True, capture_output=True, check=False,
                )
                self.assertEqual(e.returncode, 0, e.stderr)
            self.assertEqual(
                (root / "quant-a/quant_qc.summary.tsv").read_bytes(),
                (root / "quant-b/quant_qc.summary.tsv").read_bytes(),
            )
            self.assertEqual(
                (root / "exploratory-a/pca_scores.tsv").read_bytes(),
                (root / "exploratory-b/pca_scores.tsv").read_bytes(),
            )
            self.assertIn("overall_missing_values\t1", (root / "quant-a/quant_qc.summary.tsv").read_text())
            self.assertIn("eligible_complete_proteins\t3", (root / "exploratory-a/protein_cv.summary.tsv").read_text())
            with (root / "exploratory-a/pca_scores.tsv").open(encoding="utf-8", newline="") as handle:
                self.assertEqual(len(list(csv.DictReader(handle, delimiter="\t"))), 3)
            design = root / "design.tsv"
            design.write_text(
                "sample\tcondition\treplicate\nS1\ttechnical\t1\nS2\ttechnical\t2\nS3\ttechnical\t3\n",
                encoding="utf-8",
            )
            report = root / "summary.md"
            generated = subprocess.run(
                [sys.executable, str(REPORT_GENERATOR), "--matrix-summary", str(root / "matrix/protein_matrix.summary.tsv"),
                 "--quant-dir", str(root / "quant-a"), "--exploratory-dir", str(root / "exploratory-a"),
                 "--design", str(design), "--output", str(report)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(generated.returncode, 0, generated.stderr)
            text = report.read_text(encoding="utf-8")
            for section in ("## Missingness", "## Correlation and variation", "## PCA and sample distances", "## Limitations"):
                self.assertIn(section, text)
            self.assertNotIn(str(root), text)


class NextflowFailureGuardTests(unittest.TestCase):
    def module_text(self, name: str) -> str:
        return (PROJECT / "modules" / "local" / name).read_text(encoding="utf-8")

    def test_msfragger_requires_nonempty_pepxml_with_psms(self) -> None:
        source = self.module_text("msfragger_search.nf")
        self.assertIn("expected one non-empty <run name>.pepXML", source)
        self.assertIn("pepXML contains no spectrum_query records", source)

    def test_peptideprophet_has_input_and_output_guards(self) -> None:
        source = self.module_text("philosopher_peptideprophet.nf")
        self.assertIn("input pepXML is absent or empty", source)
        self.assertIn("combined.pep.xml was not produced", source)

    def test_proteinprophet_has_input_and_output_guards(self) -> None:
        source = self.module_text("philosopher_proteinprophet.nf")
        self.assertIn("PeptideProphet output is absent or empty", source)
        self.assertIn("combined.prot.xml was not produced", source)

    def test_filter_and_report_require_outputs(self) -> None:
        filter_source = self.module_text("philosopher_filter.nf")
        report_source = self.module_text("philosopher_report.nf")
        self.assertIn("filtered PSM state was not produced", filter_source)
        self.assertIn("psm.tsv peptide.tsv protein.tsv", report_source)

    def test_ionquant_failure_and_output_guards(self) -> None:
        source = self.module_text("ionquant.nf")
        self.assertIn("java -Xmx${java_xmx} -jar", source)
        self.assertNotIn("|| true", source)
        self.assertIn("IonQuant error: no non-empty", source)
        self.assertIn("output was produced", source)
        self.assertIn("summarize_quantification.py", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
