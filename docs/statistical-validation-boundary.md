# Statistical identification boundary

The synthetic search fixture tests file contracts and tool orchestration only. One synthetic MS2 spectrum cannot support stable PeptideProphet mixture modelling, ProteinProphet inference, or empirical target-decoy FDR estimation.

Philosopher 5.1.0's installed help confirms the intended future interfaces:

1. `peptideprophet` consumes search pepXML and the configured database and supports the declared decoy prefix.
2. `proteinprophet` consumes PeptideProphet output and creates protein-level inference output.
3. `filter` consumes peptide/protein XML outputs, applies explicit PSM/peptide/protein thresholds, and uses the configured decoy tag.
4. `report` materializes report tables only after validated filtering.

No statistical process is enabled in the synthetic mode. Real validation requires a search with enough target and decoy observations to evaluate model stability and FDR behaviour. Thresholds must not be weakened merely to obtain output.
