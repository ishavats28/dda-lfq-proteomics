process MSFRAGGER_SEARCH {
    tag sample

    cpus 2
    memory '5 GB'
    time '2 h'

    publishDir "${params.outdir}/identification/search", mode: 'copy', overwrite: false,
        saveAs: { name -> name.endsWith('.pepXML') ? name : null }
    publishDir "${params.outdir}/provenance", mode: 'copy', overwrite: false,
        saveAs: { name -> name.endsWith('.provenance.tsv') ? name : null }
    publishDir "${params.outdir}/identification/logs", mode: 'copy', overwrite: false,
        saveAs: { name -> name.endsWith('.log') ? name : null }

    input:
    tuple val(sample), path(mzml), path(fasta), path(fasta_manifest), path(parameter_template), path(msfragger_jar), path(preflight_report)

    output:
    tuple val(sample), path("${sample}.pepXML"), emit: pepxml
    tuple val(sample), path("${sample}.msfragger.provenance.tsv"), emit: provenance
    tuple val(sample), path("${sample}.msfragger.stdout.log"), path("${sample}.msfragger.stderr.log"), emit: logs

    script:
    """
    "${params.python}" "${projectDir}/bin/verify_tool.py" \
      --tool msfragger \
      --path "${msfragger_jar}" \
      --expected-version 4.4.1 \
      > msfragger.version.tsv

    "${params.python}" "${projectDir}/bin/materialize_msfragger_params.py" \
      --template "${parameter_template}" \
      --database "${fasta}" \
      --output search.params

    /usr/bin/time -v java -Xmx${params.msfragger_xmx} -jar "${msfragger_jar}" \
      search.params "${mzml}" \
      > "${sample}.msfragger.stdout.log" \
      2> "${sample}.msfragger.stderr.log"

    pepxml_count=\$(find . -maxdepth 1 -type f -name '*.pepXML' -size +0c | wc -l)
    if [ "\${pepxml_count}" -ne 1 ]; then
      echo "MSFragger search error: expected one non-empty <run name>.pepXML output, found \${pepxml_count}" >&2
      exit 4
    fi
    pepxml_file=\$(find . -maxdepth 1 -type f -name '*.pepXML' -size +0c -print -quit)
    if [ "\$(basename "\${pepxml_file}")" != "${sample}.pepXML" ]; then
      mv "\${pepxml_file}" "${sample}.pepXML"
    fi
    raw_psms=\$(grep -c '<spectrum_query ' "${sample}.pepXML" || true)
    if [ "\${raw_psms}" -eq 0 ]; then
      echo 'MSFragger search error: pepXML contains no spectrum_query records' >&2
      exit 5
    fi

    {
      printf 'field\tvalue\n'
      printf 'msfragger_version\t4.4.1\n'
      printf 'java_version\t%s\n' "\$(java -version 2>&1 | head -n 1)"
      printf 'java_xmx\t%s\n' "${params.msfragger_xmx}"
      printf 'threads\t2\n'
      printf 'msfragger_jar_sha256\t%s\n' "\$(sha256sum "${msfragger_jar}" | cut -d' ' -f1)"
      printf 'fasta_sha256\t%s\n' "\$(sha256sum "${fasta}" | cut -d' ' -f1)"
      printf 'mzml_sha256\t%s\n' "\$(sha256sum "${mzml}" | cut -d' ' -f1)"
      printf 'parameter_sha256\t%s\n' "\$(sha256sum search.params | cut -d' ' -f1)"
      printf 'raw_psm_records\t%s\n' "\${raw_psms}"
      printf 'pepxml_bytes\t%s\n' "\$(stat -c %s "${sample}.pepXML")"
      printf 'execution_utc\t%s\n' "\$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    } > "${sample}.msfragger.provenance.tsv"
    """
}
