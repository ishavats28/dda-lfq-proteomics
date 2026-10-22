process VALIDATE_QUANT_INPUTS {
    tag 'ionquant-inputs'

    cpus 1
    memory '256 MB'
    time '10 min'

    publishDir "${params.outdir}/metadata", mode: 'copy', overwrite: false

    input:
    tuple path(source_manifest), val(base_dir)

    output:
    path 'quantification-manifest.normalized.tsv', emit: normalized

    script:
    """
    "${params.python}" "${projectDir}/bin/validate_quant_manifest.py" \
      --input "${source_manifest}" \
      --base-dir "${base_dir}" \
      --output quantification-manifest.normalized.tsv
    """
}
