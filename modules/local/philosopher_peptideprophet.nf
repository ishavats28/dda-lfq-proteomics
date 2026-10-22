process PHILOSOPHER_PEPTIDEPROPHET {
    tag sample

    cpus 1
    memory '2 GB'
    time '2 h'

    publishDir "${params.outdir}/provenance", mode: 'copy', overwrite: false,
        saveAs: { name -> name.endsWith('.peptideprophet.provenance.tsv') ? name : null }

    input:
    tuple val(sample), path(raw_pepxml), path(fasta), path(philosopher_bin)

    output:
    tuple val(sample), path("${sample}.peptideprophet.workspace"), path('combined.pep.xml'), emit: validated
    tuple val(sample), path("${sample}.peptideprophet.provenance.tsv"), emit: provenance

    script:
    """
    test -s "${raw_pepxml}" || { echo 'PeptideProphet error: input pepXML is absent or empty' >&2; exit 4; }
    "${params.python}" "${projectDir}/bin/verify_tool.py" \
      --tool philosopher --path "${philosopher_bin}" --expected-version 5.1.0

    mkdir -p "${sample}.peptideprophet.workspace/tmp"
    cp "${raw_pepxml}" "${sample}.peptideprophet.workspace/${sample}.pepXML"
    cp "${fasta}" "${sample}.peptideprophet.workspace/database.fasta"
    tool_path=\$(readlink -f "${philosopher_bin}")
    cd "${sample}.peptideprophet.workspace"
    /usr/bin/time -v -o peptideprophet.resource.txt \
      "\${tool_path}" workspace --init --nocheck --analytics=false --temp tmp
    "\${tool_path}" database --annotate database.fasta --prefix "${params.decoy_prefix}"
    /usr/bin/time -v -o peptideprophet.resource.txt -a \
      "\${tool_path}" peptideprophet \
        --database database.fasta \
        --decoy "${params.decoy_prefix}" \
        --nonparam \
        --ppm \
        --accmass \
        --enzyme trypsin \
        --combine \
        --output combined \
        "${sample}.pepXML" \
      > peptideprophet.stdout.log 2> peptideprophet.stderr.log
    test -s combined.pep.xml || { echo 'PeptideProphet error: combined.pep.xml was not produced' >&2; exit 5; }
    cd ..
    cp "${sample}.peptideprophet.workspace/combined.pep.xml" combined.pep.xml
    {
      printf 'field\tvalue\n'
      printf 'philosopher_version\t5.1.0\n'
      printf 'decoy_prefix\t%s\n' "${params.decoy_prefix}"
      printf 'nonparametric_model\ttrue\n'
      printf 'accurate_mass\ttrue\n'
      printf 'ppm_mass_model\ttrue\n'
      printf 'enzyme\ttrypsin\n'
    } > "${sample}.peptideprophet.provenance.tsv"
    """
}
