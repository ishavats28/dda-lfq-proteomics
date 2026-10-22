# MSFragger closed-search contract

The baseline template at `conf/msfragger/closed-search.params` follows the official MSFragger closed-search parameter vocabulary. It declares DDA data, strict tryptic digestion, two missed cleavages, peptide lengths 7–50, ±20 ppm precursor tolerance, 20 ppm fragment tolerance, fixed carbamidomethyl cysteine, variable methionine oxidation, and pepXML output. It disables mass offsets, delta-mass localization, labile searching, DIA, DDA+, and additional PTM-specific modes. It also disables MSFragger's optional preliminary calibration search because the validation input is already calibrated mzML. This does not change the production search tolerances or scoring contract. The template contains exactly one `__DATABASE_NAME__` placeholder, materialized to the validated staged FASTA inside each task.

The separate `constrained-validation.params` is a low-memory integration-validation profile. Its only active search-setting difference from the production baseline is a peptide-length range of 7–35 rather than 7–50. It is an engineering accommodation for the local machine, not a replacement production profile or a claim that 7–35 is universally optimal. Both profiles exceeded the safe local memory envelope at a 4 GiB Java heap with the full reviewed-human target/decoy database.

The separate `synthetic-search.params` disables mass calibration because a single synthetic MS2 observation cannot support calibration. It remains a closed DDA tryptic search and does not relax the minimum four matched fragments.

The official command-line interface is a Java JAR accepting a parameter file followed by spectral files. The official output contract is one `<run name>.pepXML` per searched spectral file. The workflow checks for exactly one non-empty pepXML and normalizes its name to the validated sample identifier.

Each successful task records MSFragger, Java, and heap versions/settings; thread count; SHA-256 values for the JAR, FASTA, mzML, and materialized parameters; UTC execution time; stdout; stderr; and `/usr/bin/time -v` resource observations. Machine-specific source paths are not written to the repository.

MSFragger 4.4.1 has been verified with the synthetic integration fixture. Real PXD024427 searches with the full production and constrained validation profiles reached database-index construction but stopped at MSFragger's memory guard before spectrum scoring. See the identification validation report for the exact observations.
