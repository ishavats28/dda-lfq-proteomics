# Workflow architecture

## Design constraints

The workflow is intended for small DDA experiments on a workstation with approximately 8 GB RAM and limited free storage. The local executor therefore runs one task at a time by default. Processes will stage files through Nextflow, avoid copying raw data into published results, and publish only durable reports and compact result tables. Nextflow work directories remain available for recovery and are removed only by an explicit user cleanup action.

The native input remains centroided mzML. An optional explicit Thermo RAW preprocessing path invokes a user-configured official ProteoWizard `msconvert` executable, then sends its mzML output through the same validation/QC contract. ProteoWizard is not assumed or installed automatically, and scientific search processes never consume vendor RAW directly.

## Stages and contracts

1. **Input validation and mzML metadata/QC** — validate a sample sheet, unique sample identifiers, readable mzML files, and basic spectra metadata; emit normalized metadata and compact per-run pre-QC tables. This stage is implemented without plots.
2. **Database-search identification** — invoke a validated headless database-search executable for each mzML file; emit peptide-spectrum-match and search-engine result files plus logs.
3. **Target-decoy FDR filtering** — apply explicit peptide-spectrum-match, peptide, and protein-level error control against a documented target-decoy database; emit filtered tables and audit summaries.
4. **Label-free protein quantification** — quantify precursor or ion signals and aggregate them through a documented protein inference strategy; emit per-run quantitative tables.
5. **Protein-level QC and matrix preparation** — construct raw MaxLFQ and log2 protein-by-sample matrices, remove explicit decoys/contaminants, preserve missing values, and emit annotations separately. This stage is implemented.
6. **Exploratory technical analysis** — calculate missingness, distributions, pairwise-complete correlations, complete-case CV, centered/unscaled log2 PCA, and sample distances. This stage is implemented for technical QC. Biological differential analysis is guarded and is not run without a valid biological design.
7. **Reports** — collate software context, identification/LFQ counts, quantitative QC, figures, policy decisions, and limitations in a reproducible Markdown report. This stage is implemented.

Sample/mzML validation, lightweight pre-QC, FASTA validation, scientific-tool checks, optional Thermo RAW conversion, memory/disk preflight, database cache validation, modular identification/FDR, compact IonQuant LFQ, protein-matrix construction, technical quantitative QC, exploratory analysis, and report generation are implemented. Three comparable public PXD003472 yeast runs completed through conversion, individual 1% identification/FDR, combined non-MBR quantification, and technical QC. Biological differential analysis remains disabled for this technical design.

The IonQuant layer accepts an explicit TSV mapping each filesystem-safe sample to one mzML and genuine non-empty Philosopher `psm.tsv` and `protein.tsv` reports. A dedicated Nextflow process validates IonQuant 1.11.20 and the matching MSFragger native-resource directory, performs a 3.5 GiB available-memory/20 GiB disk preflight, stages copies without modifying originals, and invokes standalone IonQuant with two threads and a 3 GiB heap. The primary contract uses MS1 quantification, multi-run normalization, MaxLFQ, non-ion-mobility settings, and MBR disabled. Quantification QC is derived from IonQuant's combined tables and reports per-run completeness, overlap, missingness, distributions, and input checksums. Optional MBR is deferred after a diagnosed missing JFree runtime class during model fitting.

## Practical command-line toolchain

The selected identification stack uses MSFragger as a headless Java search engine and Philosopher as a command-line validation toolkit. IonQuant 1.11.20 performs MS1 label-free quantification. FragPipe's graphical interface is not a Nextflow process.

The downstream analysis stack uses pandas and NumPy for deterministic table handling, SciPy for correlations, and Matplotlib for non-interactive figures. Nextflow keeps matrix construction, design validation, quantitative QC, exploratory analysis, and reporting as separate dependencies. No imputation is performed by default.

ProteoWizard `msconvert` is optional for vendor-file conversion. Pre-converted mzML remains the portable input contract.

## Execution strategy

- Use the local executor with `maxForks = 1` and executor queue size 1.
- Process one mzML/search job at a time; avoid joining full spectra or PSM tables in memory.
- Keep database indices shared and immutable rather than rebuilding per sample.
- Use explicit resource labels or process-specific overrides only after measurement.
- Reserve Docker and Conda for opt-in profiles. Neither is assumed to exist.
- On Windows, execute Nextflow in WSL2 rather than treating native PowerShell as a supported Nextflow runtime.
- Capture tool versions, parameter files, database checksums, and commands in provenance outputs.
- Refuse to launch MSFragger unless Linux `MemTotal` is at least 5.5 GiB, `MemAvailable` is at least 4.25 GiB, and the project filesystem has at least 25 GiB free; use two threads, a Java heap no larger than 4 GiB, and one search task at a time.

The experimental path uses separate processes for MSFragger, PeptideProphet, ProteinProphet, Philosopher filter, report, and summary. Philosopher's `.meta` state is passed forward as an explicit workspace directory; processes do not race against a shared mutable workspace.

## Likely bottlenecks

Database searching is expected to dominate CPU and memory, with demand driven by FASTA size, variable modifications, enzyme rules, precursor tolerances, and spectrum count. Ion-level feature detection can also require substantial memory. Protein-table assembly and statistical analysis should operate on compact tables but can still inflate memory if implemented with dense copies. mzML conversion temporarily requires both vendor input and mzML output, so it needs a preflight disk-space check.

With only 8 GB installed RAM, heavy processes should normally be capped below 6 GB so the operating system remains responsive. Current free memory must be checked immediately before real analysis.

## Expected intermediate files

- Validated sample manifest and input checksums.
- Per-run mzML metadata and spectral QC tables.
- Search parameter snapshots, logs, and search-engine result files.
- Target-decoy PSM, peptide, and protein tables before and after filtering.
- Per-run ion/precursor quantification tables.
- Protein abundance matrix, annotations, missingness table, and normalization diagnostics.
- Validated design table, raw/log2 protein matrices, technical-QC tables, and compact figures.
- Software-version and provenance manifests.

Large inputs, databases, search scratch files, and transient quantification intermediates stay outside published report directories and are excluded from version control.
