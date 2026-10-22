process PHILOSOPHER_YEAST_DATABASE {
    tag 'UP000002311-reviewed-contaminants-decoys'

    cpus 1
    memory '512 MB'
    time '2 h'

    publishDir params.yeast_database_cache_dir, mode: 'copy', overwrite: false

    input:
    path philosopher_bin

    output:
    tuple path('UP000002311_reviewed_contam_rev.fasta'), path('UP000002311_reviewed_contam_rev.manifest.tsv'), emit: database

    script:
    """
    "${params.python}" "${projectDir}/bin/verify_tool.py" \
      --tool philosopher --path "${philosopher_bin}" --expected-version 5.1.0

    mkdir -p database_workspace/tmp
    tool_path=\$(readlink -f "${philosopher_bin}")
    cd database_workspace
    "\${tool_path}" workspace --init --nocheck --analytics=false --temp tmp
    "\${tool_path}" database \
      --id UP000002311 \
      --reviewed \
      --contam \
      --contamprefix \
      --prefix rev_

    fasta_count=0
    generated=''
    for candidate in ./*.fasta ./*.fas ./*.fa; do
      [ -f "\${candidate}" ] || continue
      [ -s "\${candidate}" ] || continue
      fasta_count=\$((fasta_count + 1))
      generated="\${candidate}"
    done
    if [ "\${fasta_count}" -ne 1 ]; then
      echo "Philosopher database error: expected one non-empty generated FASTA, found \${fasta_count}" >&2
      exit 4
    fi
    cp "\${generated}" ../UP000002311_reviewed_contam_rev.fasta
    cd ..

    "${params.python}" "${projectDir}/bin/validate_fasta.py" \
      --input UP000002311_reviewed_contam_rev.fasta \
      --output fasta.validation.tsv
    "${params.python}" "${projectDir}/bin/database_cache.py" create \
      --fasta UP000002311_reviewed_contam_rev.fasta \
      --manifest UP000002311_reviewed_contam_rev.manifest.tsv \
      --database-id UP000002311-reviewed-contam-rev \
      --source UniProtKB \
      --source-accession UP000002311 \
      --taxonomy-id 559292 \
      --organism 'Saccharomyces cerevisiae strain ATCC 204508 / S288c' \
      --review-status reviewed-Swiss-Prot \
      --philosopher-version 5.1.0 \
      --contaminants philosopher-common-contaminants \
      --decoy-strategy philosopher-reverse \
      --decoy-prefix rev_ \
      --contaminant-prefix contam_
    """
}
