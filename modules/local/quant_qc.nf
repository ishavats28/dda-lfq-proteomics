process QUANTITATIVE_QC {
    tag 'quantitative-qc'
    cpus 1
    memory '1 GB'
    time '30 min'
    publishDir "${params.outdir}/qc", mode: 'copy', overwrite: false

    input:
    tuple path(matrix), path(design), path(identification_summary)

    output:
    tuple path(matrix), path(design), path('quant-qc'), emit: qc

    script:
    """
    "${params.python}" "${projectDir}/bin/quant_qc.py" \
      --raw-matrix "${matrix}/protein_matrix.raw.tsv" \
      --log2-matrix "${matrix}/protein_matrix.log2.tsv" \
      --identification-summary "${identification_summary}" \
      --outdir quant-qc
    """
}
