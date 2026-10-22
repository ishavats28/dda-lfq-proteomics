process PHILOSOPHER_DATABASE_PREP {
    tag 'workspace-and-database'

    cpus 1
    memory '512 MB'
    time '30 min'

    publishDir "${params.outdir}/philosopher", mode: 'copy', overwrite: false,
        saveAs: { filename -> filename == 'philosopher_database_provenance.tsv' ? filename : null }

    input:
    tuple path(fasta), path(fasta_manifest)
    path philosopher_bin
    val decoy_prefix

    output:
    path 'philosopher_workspace', emit: workspace
    path 'philosopher_database_provenance.tsv', emit: provenance

    script:
    """
    "${params.python}" "${projectDir}/bin/verify_tool.py" \
      --tool philosopher \
      --path "${philosopher_bin}" \
      --expected-version 5.1.0 \
      > philosopher.version.tsv

    mkdir -p philosopher_workspace/tmp
    cp "${fasta}" philosopher_workspace/input.fasta
    cp "${fasta_manifest}" philosopher_workspace/fasta.validation.tsv
    tool_path=\$(readlink -f "${philosopher_bin}")

    cd philosopher_workspace
    "\${tool_path}" workspace --init --nocheck --analytics=false --temp tmp
    "\${tool_path}" database --annotate input.fasta --prefix "${decoy_prefix}"
    test -s .meta/meta.bin
    test -s .meta/db.bin
    "\${tool_path}" version > philosopher.version.log 2>&1
    cd ..

    archive_sha256=\$(sha256sum "${philosopher_bin}" | cut -d' ' -f1)
    fasta_sha256=\$(sha256sum "${fasta}" | cut -d' ' -f1)
    {
      printf 'field\tvalue\n'
      printf 'philosopher_version\t5.1.0\n'
      printf 'philosopher_executable_sha256\t%s\n' "\${archive_sha256}"
      printf 'platform\tlinux_amd64\n'
      printf 'fasta_sha256\t%s\n' "\${fasta_sha256}"
      printf 'decoy_prefix\t%s\n' "${decoy_prefix}"
      printf 'workspace_initialized\ttrue\n'
      printf 'database_annotated\ttrue\n'
    } > philosopher_database_provenance.tsv
    """
}
