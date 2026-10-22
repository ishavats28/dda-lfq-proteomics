# FASTA provenance manifest

Every production search database must have an explicit, version-controlled provenance record even though the FASTA itself remains local and ignored.

| Field | Meaning |
|---|---|
| `database_id` | Stable project identifier for the database build. |
| `source` | Source organization or explicit `synthetic` label. |
| `source_accession` | Proteome/database accession where applicable. |
| `taxonomy_id` | Declared taxonomy identifier; never inferred from sequences. |
| `organism` | Declared organism name; never inferred from sequences. |
| `review_status` | Reviewed, unreviewed, mixed, or not applicable. |
| `retrieval_date` | ISO 8601 source retrieval date. |
| `original_sha256` | SHA-256 of the retrieved source file. |
| `contaminants` | Contaminant source/version and merge policy, or `none`. |
| `decoy_strategy` | Supported generating tool and strategy. |
| `decoy_prefix` | Prefix used to identify decoy records. |
| `generator` | Database-generating tool. |
| `generator_version` | Exact generating-tool version. |
| `final_sha256` | SHA-256 of the final search FASTA. |

The machine-generated validation manifest is separate and records filename, resolved local path, record count, amino-acid count, SHA-256, and validation status. Local resolved paths belong only in ignored execution results.

The repository example is structural. Synthetic fixtures must use `source=synthetic`; empty taxonomy fields must not be interpreted as inferred metadata.
