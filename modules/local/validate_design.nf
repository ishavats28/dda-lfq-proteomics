process VALIDATE_ANALYSIS_DESIGN {
    tag 'analysis-design'
    cpus 1
    memory '256 MB'
    time '10 min'
    publishDir "${params.outdir}/metadata", mode: 'copy', overwrite: false,
        saveAs: { name -> name == 'design.normalized.tsv' ? name : null }

    input:
    tuple path(matrix), path(design)

    output:
    tuple path(matrix), path('design.normalized.tsv'), emit: validated

    script:
    """
    "${params.python}" "${projectDir}/bin/validate_design.py" \
      --design "${design}" --matrix "${matrix}/protein_matrix.raw.tsv" \
      --output design.normalized.tsv
    """
}
