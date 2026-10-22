# Experimental design contract

The reusable design table is tab-separated and requires `sample`, `condition`, and `replicate`. Optional `batch`, `subject`, and `fraction` fields may be empty. Sample identifiers must be unique and filesystem-safe, conditions must be explicit and non-empty, and replicate values must be positive integers. A complete design must contain every quantitative matrix sample exactly once, and every design sample must exist in that matrix. Metadata are never inferred from filenames.

The current PXD003472 D1, D2, and D3 runs form one technical validation set under one condition. They are comparable repeat measurements used for quantitative pipeline QC, not independent biological case/control observations.

Future biological differential analysis has an additional guard: at least two conditions and at least two independent biological replicates per condition are mandatory, while three or more are recommended. Technical repeats cannot be declared as independent biological replicates. When subjects or batches are supplied, they remain explicit design factors rather than being hidden or inferred.

Primary quantitative QC uses no imputation. Pairwise calculations use proteins observed in both samples; CV and PCA use explicitly reported complete cases.
