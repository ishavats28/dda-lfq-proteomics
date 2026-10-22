# Tests

Run the deterministic Python contract tests from the project root with the pinned local environment:

```bash
.venv/bin/python tests/run_tests.py
```

Set `PHILOSOPHER_BIN` and, when an officially licensed JAR is present, `MSFRAGGER_JAR` to include installed-tool version checks. An absent licensed MSFragger JAR is reported as a skipped/not-run test, never as a pass.

Set `IONQUANT_JAR` to include the installed IonQuant 1.11.20 version check. IonQuant contract tests use only repository-safe synthetic tables; they do not fabricate scientific quantification.

Run the infrastructure-only Nextflow path with:

```bash
nextflow run main.nf -profile standard --smoke
```

Run the validation and mzML pre-QC fixture path with:

```bash
nextflow run main.nf -profile standard \
  --samplesheet tests/fixtures/valid_samplesheet.tsv \
  --python "$PWD/.venv/bin/python"
```

Files under `tests/fixtures/` are tiny synthetic infrastructure fixtures. They do not represent biological measurements and must not be used to validate scientific performance.

RAW-conversion tests generate a tiny temporary `.raw`-named contract input and use `tests/fixtures/tools/fake_msconvert.py`. That stand-in only exercises error handling and the mzML-QC handoff; it is not a vendor-data converter and is never used for scientific analysis.

The separate `tests/fixtures/search/` dataset exercises FASTA, mzML, parameter, and tool interfaces. Its single synthetic MS2 observation is insufficient for statistical identification or FDR validation.
