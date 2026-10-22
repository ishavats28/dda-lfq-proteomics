process BUILD_PROTEIN_MATRIX {
    tag 'protein-matrix'
    cpus 1
    memory '1 GB'
    time '30 min'
    publishDir "${params.outdir}/matrix", mode: 'copy', overwrite: false

    input:
    path protein_table

    output:
    path 'matrix', emit: matrix

    script:
    """
    "${params.python}" "${projectDir}/bin/build_protein_matrix.py" \
      --protein "${protein_table}" --outdir matrix
    """
}
