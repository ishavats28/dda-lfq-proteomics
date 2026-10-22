# Label-free quantification validation

## Scope

IonQuant 1.11.20 was validated on three comparable pure-yeast Q Exactive HF 500 ng, 60-minute DDA runs from PXD003472. D1, D2, and D3 are technical validation runs, not independent biological groups. The primary validated path uses MS1 quantification, between-run normalization, MaxLFQ, unique-plus-razor peptides, two threads, a 3 GiB heap, and match-between-runs disabled.

## Provenance

- IonQuant JAR SHA-256: `c38e3cc75dfb82f0b991d49397a49b6e8b98879f804018171d23db0fb3bbb8e3`.
- Java: OpenJDK 17.0.20.1.
- FASTA SHA-256: `61ddd969e489fe444fe4dc1d2e638ee97692acbef483048b0e4c2f346e65177e`.
- Official MSFragger 4.4.1 native resources were used without redistribution.

## Runs and identification inputs

| Run | RAW bytes | mzML bytes | Spectra (MS1/MS2) | Raw PSMs | Filtered PSMs | Unique peptides | Proteins/groups |
|---|---:|---:|---:|---:|---:|---:|---:|
| D1 | 894,270,674 | 350,370,690 | 44,448 (6,639/37,809) | 24,657 | 14,663 | 11,112 | 2,189 |
| D2 | 882,978,736 | 347,611,398 | 44,282 (6,743/37,539) | 25,049 | 16,328 | 12,281 | 2,271 |
| D3 | 837,428,418 | 337,488,347 | 43,872 (6,746/37,126) | 23,882 | 15,628 | 11,766 | 2,242 |

The converted mzML SHA-256 values were:

- D1: `0b1fa9d7c139984291af0a7763830603a4e305956978724c08634f5dafb7bf38`;
- D2: `88d0034b36870f1be6529b22e1d3ded5d7c08ba3f6a9b5c4c679ee98d01ef5a6`;
- D3: `70ab509f1875a0b039c56940e0e977dbf0a5713d2fca38ec15ce7c464ff559b9`.

## IonQuant results

Single-run D1 quantification reported 13,406 ions, 11,112 peptides, 2,189 proteins, and 2,058 proteins with non-zero intensity. IonQuant correctly did not calculate MaxLFQ from one experiment.

The three-run non-MBR analysis completed in 67.37 seconds with 1,372,724 kB peak RSS and no swaps.

| Combined result | Count |
|---|---:|
| Ions | 20,148 |
| Peptides | 16,451 |
| Protein rows | 2,859 |
| Proteins with non-zero MaxLFQ | 1,912 |
| Proteins quantified in all runs | 1,682 |

The full 2,859 × 3 source protein-intensity table contained 25.99% missing/zero entries. Non-zero protein counts were 2,065 for D1, 2,147 for D2, and 2,136 for D3. The overall median non-zero intensity was 43,274,928.

## Optional match-between-runs limitation

MBR was attempted only after the non-MBR result succeeded. IonQuant reached feature extraction, LDA, and mixture-model fitting, then stopped with `NoClassDefFoundError: org/jfree/data/xy/IntervalXYDataset`. The official standalone JAR lacked the required JFree class, while the official `ext` bundle supplied native instrument resources rather than that Java dependency. No unofficial dependency workaround was introduced.

The successful non-MBR analysis remains the primary validated LFQ path. No biological differential-abundance inference was performed.
