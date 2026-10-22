process VALIDATE_DATABASE_CACHE {
    tag 'UP000005640-cache'

    cpus 1
    memory '256 MB'
    time '10 min'

    input:
    tuple path(fasta), path(manifest)

    output:
    tuple path(fasta), path(manifest), emit: database

    script:
    """
    "${params.python}" "${projectDir}/bin/database_cache.py" verify \
      --fasta "${fasta}" \
      --manifest "${manifest}"
    "${params.python}" "${projectDir}/bin/validate_fasta.py" \
      --input "${fasta}" \
      --output cached_fasta.validation.tsv
    """
}
