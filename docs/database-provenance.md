# Protein database provenance contract

Protein FASTA is an explicit workflow input for search and database preparation. The default pipeline never silently downloads, updates, or replaces a protein sequence database. FASTA is not required for infrastructure smoke testing or mzML pre-QC.

## Human validation baseline

For a future small human validation experiment, the initial database candidate is the reviewed Swiss-Prot subset of the UniProt human reference proteome, taxon 9606 and proteome accession `UP000005640`. The exact exported entry set must be appropriate to the selected validation experiment and captured at retrieval time. The authoritative proteome landing page is `https://www.uniprot.org/proteomes/UP000005640`.

Reviewed sequences are preferred for the small local validation because they limit database size and search space. Expansion to unreviewed sequences, isoforms, variants, or experiment-specific proteins requires an explicit scientific justification.

For the PXD024427 validation path, the explicit `--prepare_database` mode invokes Philosopher 5.1.0 with proteome ID `UP000005640`, `--reviewed`, common contaminants, contaminant prefixing, reverse decoys, and decoy prefix `rev_`. Ordinary analysis mode never invokes this network-backed operation. The resulting ignored cache contains a FASTA plus a manifest recording generation time, version, strategy, record counts, SHA-256, and byte size.

If both cache files exist, preparation validates their filename, byte size, and SHA-256 and reuses them. An incomplete or mismatched cache fails rather than downloading or regenerating silently.

## Yeast local-validation database

The yeast validation uses UniProt reference proteome `UP000002311`. Current UniProt metadata identifies it as the reference proteome for *Saccharomyces cerevisiae* strain ATCC 204508 / S288c, taxon 559292, with all 6,067 proteome proteins reviewed as of the metadata check. The explicit `--prepare_yeast_database` mode uses Philosopher 5.1.0 with `--reviewed`, common contaminants, contaminant prefixing, reverse decoys, and `rev_`. Its ignored cache is independent from the human cache and is verified before reuse.

## Required provenance record

Before a database is accepted for searching, record:

- source organization and exact download URL or accession;
- retrieval date in ISO 8601 format;
- cryptographic checksum of the downloaded source and generated search database;
- taxonomy identifier and organism;
- reviewed/unreviewed status and isoform policy;
- contaminant source, version, prefixes, and merge procedure;
- target/decoy strategy, decoy prefix, generating tool, and exact tool version;
- any header normalization or sequence filtering.

The contaminant collection has not yet been selected. It must be versioned and checksummed rather than copied without provenance. Contaminants must remain distinguishable in downstream reports.

Target/decoy generation and interpretation will be delegated to a validated, supported scientific tool in the selected identification stack. It will not be reproduced in an ad-hoc sequence-reversal script. The tool/version, settings, and resulting checksum must be recorded.

The implemented validator checks readable regular files, accepted FASTA extensions, non-empty headers and sequences, protein-compatible characters, unique complete identifiers, record count, amino-acid count, and SHA-256. It does not infer organism or taxonomy. See `docs/fasta-manifest.md` for the reusable provenance schema.

The repository search fixture contains documented, precomputed reversed records solely for target/decoy interface testing. It is not the production decoy-generation method and cannot validate FDR estimation.

Downloaded and generated FASTA files, decoy databases, search indices, and local database caches are excluded from version control. Only small metadata, checksums, and parameter records belong in the repository.
