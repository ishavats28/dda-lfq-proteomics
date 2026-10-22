process MZML_QC {
    tag sample

    cpus 1
    memory '512 MB'
    time '30 min'

    publishDir "${params.outdir}/qc", mode: 'copy', overwrite: false

    input:
    tuple val(sample), path(mzml)

    output:
    tuple val(sample), path("${sample}.mzml_qc.tsv"), emit: qc

    script:
    """
    "${params.python}" "${projectDir}/bin/mzml_qc.py" \
      --sample "${sample}" \
      --input "${mzml}" \
      --output "${sample}.mzml_qc.tsv" \
      --expected-pymzml-version 2.7.0
    """
}
