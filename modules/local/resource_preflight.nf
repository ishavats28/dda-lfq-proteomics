process SEARCH_RESOURCE_PREFLIGHT {
    tag 'msfragger-memory'

    cpus 1
    memory '64 MB'
    time '5 min'

    input:
    tuple val(minimum_total_gib), val(minimum_available_gib), val(minimum_free_disk_gib)

    output:
    path 'resource_preflight.tsv', emit: report

    script:
    """
    "${params.python}" "${projectDir}/bin/resource_preflight.py" \
      --minimum-total-gib "${minimum_total_gib}" \
      --minimum-available-gib "${minimum_available_gib}" \
      --minimum-free-disk-gib "${minimum_free_disk_gib}" \
      --path "${projectDir}" \
      --output resource_preflight.tsv
    """
}
