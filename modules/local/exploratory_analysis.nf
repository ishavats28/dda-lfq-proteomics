process EXPLORATORY_TECHNICAL_QC {
    tag 'exploratory-technical-qc'
    cpus 2
    memory '2 GB'
    time '30 min'
    publishDir "${params.outdir}/qc", mode: 'copy', overwrite: false

    input:
    path matrix

    output:
    tuple path(matrix), path('exploratory-qc'), emit: analysis

    script:
    """
    "${params.python}" "${projectDir}/bin/exploratory_analysis.py" \
      --raw-matrix "${matrix}/protein_matrix.raw.tsv" \
      --log2-matrix "${matrix}/protein_matrix.log2.tsv" \
      --outdir exploratory-qc
    """
}
