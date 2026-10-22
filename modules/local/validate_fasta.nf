process VALIDATE_FASTA {
    tag 'protein-database'

    cpus 1
    memory '256 MB'
    time '10 min'

    publishDir "${params.outdir}/database", mode: 'copy', overwrite: false,
        saveAs: { filename -> filename == 'fasta.validation.tsv' ? filename : null }

    input:
    path fasta

    output:
    tuple path(fasta), path('fasta.validation.tsv'), emit: validated

    script:
    """
    "${params.python}" "${projectDir}/bin/validate_fasta.py" \
      --input "${fasta}" \
      --output fasta.validation.tsv
    """
}
