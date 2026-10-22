# Synthetic MSFragger integration fixture

This directory contains deterministic, non-biological files for interface testing only. They do not model a complete instrument run and cannot support statistical FDR validation.

`synthetic_proteins.fasta` contains three small target sequences and three test-only reversed decoys prefixed with `rev_`. The reversed records were precomputed solely to exercise target/decoy-aware interfaces. They are not the production database-generation method.

`synthetic_search.mzML` is created with `generate_fixture.py`. Its single MS2 spectrum represents the unoxidized, carbamidomethyl-cysteine peptide `ACDEFGHILMNPQRSTK` at charge 2. It contains all singly charged theoretical b/y fragment masses plus six deterministic low-intensity noise peaks. The file also contains one synthetic MS1 spectrum and explicit precursor/isolation information.

Regenerate it from this directory with:

```bash
python3 generate_fixture.py
```

Expected integration-level outcomes, if the licensed MSFragger 4.4.1 JAR is present and the RAM preflight passes:

- the mzML and FASTA contracts pass;
- MSFragger accepts the materialized test parameter file;
- one non-empty `<run name>.pepXML` file is produced;
- the intended peptide is available as a candidate match.

The fixture is too small for PeptideProphet, ProteinProphet, or FDR modelling. No expected probability, q-value, protein significance, or biological conclusion is defined.
