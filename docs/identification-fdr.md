# Identification and FDR process contract

The single-run identification path uses the production closed-search parameter template, MSFragger 4.4.1, and Philosopher 5.1.0. It is distinct from the one-spectrum synthetic integration mode.

PeptideProphet is configured for tryptic peptides with the accurate-mass and ppm models and semi-parametric target-decoy modelling (`--nonparam` together with `--decoy rev_`). It consumes the genuine MSFragger pepXML and the exact search FASTA. ProteinProphet consumes the combined PeptideProphet output. Philosopher filtering uses picked and razor protein handling with PSM, peptide, and protein FDR limits of 0.01. Sequential filtering and modification mapping are not enabled for this conventional closed search.

Each command runs in its own DSL2 process. Because Philosopher persists annotated database and identification state under `.meta`, each downstream process receives an explicit copy of the preceding workspace and validates its required XML or binary state before continuing. Nextflow terminates the branch after a non-zero upstream exit, so a partial run cannot reach report generation or summary creation.

The standard Philosopher report is expected to produce non-empty `psm.tsv`, `peptide.tsv`, and `protein.tsv`. The summary script counts rows from those filtered reports and raw `<spectrum_query>` records from MSFragger pepXML. It reports Philosopher's configured thresholds descriptively and does not independently estimate FDR.

No freequant command is used. IonQuant remains outside this block.
