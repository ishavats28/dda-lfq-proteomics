# Input sample-sheet contract

The baseline workflow accepts a UTF-8, tab-separated sample sheet. The first row is a header. Field names are case-sensitive, biological metadata is never inferred from filenames, and unsupported columns are rejected to expose spelling mistakes early.

## Columns

| Column | Required | Contract |
|---|---:|---|
| `sample` | yes | Unique filesystem-safe identifier. It must begin with an ASCII letter or digit and may contain only letters, digits, `.`, `_`, or `-`. |
| `condition` | yes | Non-empty biological condition label. |
| `replicate` | yes | Positive integer. Values are normalized to their decimal integer representation. |
| `mzml` | yes | Existing readable regular file whose name ends in `.mzML`, compared case-insensitively. |
| `batch` | no | Optional batch label; may be empty. |
| `fraction` | no | Optional fraction label; may be empty. |

Every row must contain the same number of tab-separated fields as the header. Blank lines are ignored. Duplicate sample identifiers and duplicate resolved mzML paths are rejected. URLs, directories, vendor raw files, mzXML, MGF, and arbitrary files are outside the baseline input contract.

## Optional Thermo RAW conversion

The sample-sheet contract remains mzML-only. Thermo RAW is supported through a separate explicit preprocessing mode that requires `--convert_raw`, one readable `.raw` file, a filesystem-safe `--raw_sample`, and an explicit `--msconvert_bin` path. The conversion process invokes official ProteoWizard `msconvert`, writes centroided mzML with the vendor peak-picking filter `peakPicking vendor msLevel=1-`, and hands the resulting mzML to the existing streaming QC process. It does not truncate scans, threshold intensities, or clip m/z ranges.

`msconvert` is not bundled or installed automatically. The configured executable must report the documented `--mzML`, `--filter`, `--outdir`, and `--outfile` interfaces. Pre-converted mzML remains the normal portable input and does not require ProteoWizard.

Relative mzML paths are resolved against the directory containing the source sample sheet, not the Nextflow work directory or the shell's current directory. The validator emits an absolute normalized path. Environment variables are not expanded. In WSL2, sample sheets should use WSL-visible paths.

## Quantification manifest

IonQuant execution uses a separate TSV with the required logical fields `sample`, `mzml`, `psm`, and `protein`. `sample` must be unique and filesystem-safe. `mzml` must resolve to a readable non-empty `.mzML` file. `psm` and `protein` must resolve to readable, non-empty Philosopher reports named `psm.tsv` and `protein.tsv`. The PSM report must contain Spectrum, Peptide, Protein, and PeptideProphet Probability columns; the protein report must contain a Protein column. Both reports must contain data rows. URLs, duplicate samples, duplicate mzML paths, directories, missing files, malformed rows, and arbitrary report filenames are rejected before IonQuant starts. Relative paths resolve against the manifest directory. See `assets/quantification-manifest.example.tsv`.

Validation completes before mzML QC or any future expensive scientific process starts. Errors identify the input row and, when available, the sample and path.

## Minimal example

```text
sample	condition	replicate	mzml	batch	fraction
example_01	reference	1	/path/to/example_01.mzML		
```

The repository example at `assets/samplesheet.example.tsv` is structural only and does not refer to a real sample. The normalized output always uses this column order:

```text
sample, condition, replicate, mzml, batch, fraction
```

The actual file is TSV; commas above are included only for readability.
