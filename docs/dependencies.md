# Dependencies

## Currently required infrastructure

| Dependency | Version used | Purpose |
|---|---:|---|
| Nextflow | 26.04.6 | Required DSL2 orchestrator |
| OpenJDK | 17.0.20.1 | Nextflow runtime; also satisfies the Java 11+ requirement of MSFragger and IonQuant |
| Python | 3.14.4 | Input validation and mzML pre-QC |
| pymzML | 2.7.0 | Streaming mzML inspection |
| NumPy | 2.5.3 | Matrix operations and centered PCA decomposition |
| pandas | 2.3.3 | Protein-table and design-table handling |
| SciPy | 1.18.0 | Pairwise correlations and quantitative summaries |
| Matplotlib | 3.10.7 | Non-interactive quantitative-QC figures |

Python project dependencies are pinned in `requirements.txt` and should be installed into the ignored `.venv/` directory. The official pymzML 2.7.0 package metadata requires Python 3.13 or newer and lists Python 3.14 support: `https://pypi.org/project/pymzml/2.7.0/`.

The audited WSL Python lacks the optional `ensurepip` component. Recreating `.venv/` with the standard `python -m venv` workflow therefore requires the distribution package that provides venv/ensurepip, or an equivalent documented project-local pip bootstrap. This does not affect the currently verified ignored environment.

Docker and Conda are optional. They are disabled in the standard profile and are not needed for the current workflow stages.

## Scientific dependencies

| Tool | Candidate pin | Verified status and constraints |
|---|---:|---|
| MSFragger | 4.4.1 | Installed in ignored local storage and verified with Java 17. The JAR SHA-256 is `56b15a35060e1aa3b38508eed5e1b21ce697918bad75b450307160c86c652112`. The official changelog records this version and Java 11+: `https://msfragger.nesvilab.org/CHANGELOG.html`. The standalone JAR is separately licensed for academic/non-commercial use, was obtained through `https://msfragger-upgrader.nesvilab.org/upgrader/`, and must not be redistributed here. Full reviewed-human target/decoy searches using both the production 7–50 and constrained 7–35 profiles exceeded the mandated 4 GiB heap; see `validation/identification-validation.md`. |
| IonQuant | 1.11.20 | The official JAR is installed in ignored local storage and reports exactly 1.11.20 with Java 17. Its SHA-256 is `c38e3cc75dfb82f0b991d49397a49b6e8b98879f804018171d23db0fb3bbb8e3`. The official MSFragger 4.4.1 `ext` resources are verified, and single- plus three-run non-MBR quantification completed. Optional MBR reached model fitting but failed because the standalone JAR lacked `org/jfree/data/xy/IntervalXYDataset`; no unofficial dependency was added. The official changelog records release 1.11.20 on 2026-01-13 and Java 11+: `https://github.com/Nesvilab/IonQuant/blob/master/CHANGELOG.md`. The official README documents standalone use, the `ext` resource requirement, and academic/non-commercial licensing: `https://github.com/Nesvilab/IonQuant`. |
| Philosopher | 5.1.0 | Installed locally from the official Linux amd64 release and detected as v5.1.0 build 202311202158: `https://github.com/Nesvilab/philosopher/releases/tag/v5.1.0`. Philosopher is GPL-3.0. |
| ProteoWizard msconvert | 4.0.26282 | Optional Thermo RAW conversion dependency, verified as a Windows executable callable from WSL with translated input/output paths. The local executable SHA-256 is `3ff2a75dec4c6796edff10220a12a1b571a222be12db1d7a61815aea0996f4e7`. Obtain official builds from `https://proteowizard.sourceforge.io/download.html` and configure `--msconvert_bin`; the binary is not downloaded or bundled by the workflow. The official interface documentation is `https://proteowizard.sourceforge.io/tools/msconvert.html`. |

The available Java 17 runtime satisfies the stated Java 11+ requirement for MSFragger and IonQuant. MSFragger and IonQuant require attention to their academic/non-commercial license terms before download or use.

The local Philosopher archive SHA-256 is `cf15a2d6321ecb530170b2410f5873f89e283b52d5f1ab0f27eebc124f4f4a1a`; the extracted Linux amd64 executable SHA-256 is `1065274f2d3dba1fd73c7ac5baf46bbd5b836d5142eae20556415ba089828e28`. Both files are under ignored `.local/` storage.

FragPipe's graphical application is not the workflow engine, and Nextflow remains the required orchestrator. ProteoWizard remains optional for separately scoped vendor-file conversion. Local binaries, archives, licensed JARs, and private license material remain outside version-controlled content.
