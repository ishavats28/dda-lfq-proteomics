process GENERATE_QUANTITATIVE_REPORT {
    tag 'quantitative-report'
    cpus 1
    memory '512 MB'
    time '15 min'
    publishDir "${params.outdir}/report", mode: 'copy', overwrite: false,
        saveAs: { name -> name == 'summary.md' ? name : null }
    publishDir "${params.outdir}/figures", mode: 'copy', overwrite: false,
        saveAs: { name -> name.endsWith('.png') ? name.tokenize('/').last() : null }

    input:
    tuple path(matrix), path(design), path(quant_qc), path(exploratory_qc)

    output:
    path 'summary.md', emit: report
    path 'figures/*.png', emit: figures

    script:
    """
    "${params.python}" "${projectDir}/bin/generate_report.py" \
      --matrix-summary "${matrix}/protein_matrix.summary.tsv" \
      --quant-dir "${quant_qc}" --exploratory-dir "${exploratory_qc}" \
      --design "${design}" --dataset "${params.analysis_dataset}" \
      --output summary.md
    mkdir figures
    cp "${quant_qc}"/figures/*.png figures/
    cp "${exploratory_qc}"/figures/*.png figures/
    """
}
