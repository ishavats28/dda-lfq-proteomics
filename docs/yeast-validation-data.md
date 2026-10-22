# Yeast validation data

The validation dataset is ProteomeXchange `PXD003472`, titled "S. cerevisiae DDA orbitrap-based benchmark datasets" in PRIDE. The selected run is `QExactiveHF_D1__500ng_60min.raw`, a pure 500 ng *Saccharomyces cerevisiae* digest acquired by DDA on a Q Exactive HF with a 60-minute method. The official PRIDE file record reports 894,270,674 bytes. Only this one RAW was downloaded from the official PXD003472 archive; its SHA-256 is `1a833ad3aa74b74802eef207d45debed42f0153de029ecbfaab633fb832b09f6`.

The associated publication is Jarnuczak AF, Lee DC, Lawless C, Holman SW, Eyers CE, and Hubbard SJ, "Analysis of Intrinsic Peptide Detectability via Integrated Label-Free and SRM-Based Absolute Quantitative Proteomics," *Journal of Proteome Research* 15(9), 2945-2959 (2016), DOI `10.1021/acs.jproteome.6b00048`, PubMed 27454336. The deposited sample description identifies the biological material as *S. cerevisiae* strain BY4742-derived lysate; no additional sample attributes are inferred here.

Official ProteoWizard `msconvert` 4.0.26282 converted the RAW to centroided indexed mzML with the vendor filter `peakPicking vendor msLevel=1-`. The mzML is 350,370,690 bytes with SHA-256 `0b1fa9d7c139984291af0a7763830603a4e305956978724c08634f5dafb7bf38`. Streaming QC found 44,448 total spectra, 6,639 MS1 spectra, 37,809 MS2 spectra, precursor information, and non-empty peak arrays for every spectrum.

The database is the reviewed UniProt reference proteome `UP000002311`, identified by UniProt as *Saccharomyces cerevisiae* strain ATCC 204508 / S288c, taxon 559292. Philosopher 5.1.0 adds its common contaminants and deterministic reverse decoys using prefix `rev_`. This database strain is the UniProt reference strain and differs from the deposited experimental strain; that distinction is retained in provenance rather than inferred away.

The complete single-run identification/FDR result is recorded in `validation/identification-validation.md`. Raw data, converted mzML, database files, search intermediates, and reports remain local ignored artifacts.
