process PHILOSOPHER_HUMAN_DATABASE {
    tag 'UP000005640-reviewed-contaminants-decoys'

    cpus 1
    memory '512 MB'
    time '2 h'

    publishDir params.database_cache_dir, mode: 'copy', overwrite: false

    input:
    path philosopher_bin

    output:
    tuple path('UP000005640_reviewed_contam_rev.fasta'), path('UP000005640_reviewed_contam_rev.manifest.tsv'), emit: database

    script:
    """
    "${params.python}" "${projectDir}/bin/verify_tool.py" \
      --tool philosopher --path "${philosopher_bin}" --expected-version 5.1.0

    mkdir -p database_workspace/tmp
    tool_path=\$(readlink -f "${philosopher_bin}")
    cd database_workspace
    "\${tool_path}" workspace --init --nocheck --analytics=false --temp tmp
    "\${tool_path}" database \
      --id UP000005640 \
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
    cp "\${generated}" ../UP000005640_reviewed_contam_rev.fasta
    cd ..

    "${params.python}" "${projectDir}/bin/validate_fasta.py" \
      --input UP000005640_reviewed_contam_rev.fasta \
      --output fasta.validation.tsv
    "${params.python}" "${projectDir}/bin/database_cache.py" create \
      --fasta UP000005640_reviewed_contam_rev.fasta \
      --manifest UP000005640_reviewed_contam_rev.manifest.tsv \
      --database-id UP000005640-reviewed-contam-rev \
      --source UniProtKB \
      --source-accession UP000005640 \
      --taxonomy-id 9606 \
      --organism 'Homo sapiens' \
      --review-status reviewed-Swiss-Prot \
      --philosopher-version 5.1.0 \
      --contaminants philosopher-common-contaminants \
      --decoy-strategy philosopher-reverse \
      --decoy-prefix rev_ \
      --contaminant-prefix contam_
    """
}
