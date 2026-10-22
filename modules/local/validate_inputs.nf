process VALIDATE_INPUTS {
    tag 'sample-sheet'

    cpus 1
    memory '256 MB'
    time '10 min'

    publishDir "${params.outdir}/metadata", mode: 'copy', overwrite: false

    input:
    path samplesheet
    val samplesheet_base_dir

    output:
    path 'samplesheet.normalized.tsv', emit: normalized

    script:
    """
    "${params.python}" "${projectDir}/bin/validate_samplesheet.py" \
      --input "${samplesheet}" \
      --base-dir "${samplesheet_base_dir}" \
      --output samplesheet.normalized.tsv
    """
}
