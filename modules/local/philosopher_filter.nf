process PHILOSOPHER_FILTER {
    tag sample

    cpus 1
    memory '1 GB'
    time '1 h'

    publishDir "${params.outdir}/provenance", mode: 'copy', overwrite: false,
        saveAs: { name -> name.endsWith('.filter.provenance.tsv') ? name : null }

    input:
    tuple val(sample), path(previous_workspace), path(peptide_xml), path(protein_xml), path(philosopher_bin)

    output:
    tuple val(sample), path("${sample}.filter.workspace"), path('combined.pep.xml'), path('combined.prot.xml'), emit: filtered
    tuple val(sample), path("${sample}.filter.provenance.tsv"), emit: provenance

    script:
    """
    test -s "${peptide_xml}" || { echo 'Philosopher filter error: pepXML is absent or empty' >&2; exit 4; }
    test -s "${protein_xml}" || { echo 'Philosopher filter error: protXML is absent or empty' >&2; exit 4; }
    cp -a "${previous_workspace}" "${sample}.filter.workspace"
    cp "${peptide_xml}" "${sample}.filter.workspace/combined.pep.xml"
    cp "${protein_xml}" "${sample}.filter.workspace/combined.prot.xml"
    tool_path=\$(readlink -f "${philosopher_bin}")
    cd "${sample}.filter.workspace"
    /usr/bin/time -v -o filter.resource.txt \
      "\${tool_path}" filter \
        --pepxml combined.pep.xml \
        --protxml combined.prot.xml \
        --tag "${params.decoy_prefix}" \
        --psm "${params.psm_fdr}" \
        --pep "${params.peptide_fdr}" \
        --prot "${params.protein_fdr}" \
        --picked \
        --razor \
      > filter.stdout.log 2> filter.stderr.log
    test -s .meta/psm.bin || { echo 'Philosopher filter error: filtered PSM state was not produced' >&2; exit 5; }
    test -s .meta/pro.bin || test -s .meta/prot.bin || { echo 'Philosopher filter error: filtered protein state was not produced' >&2; exit 5; }
    cd ..
    cp "${sample}.filter.workspace/combined.pep.xml" combined.pep.xml
    cp "${sample}.filter.workspace/combined.prot.xml" combined.prot.xml
    {
      printf 'field\tvalue\n'
      printf 'psm_fdr\t%s\n' "${params.psm_fdr}"
      printf 'peptide_fdr\t%s\n' "${params.peptide_fdr}"
      printf 'protein_fdr\t%s\n' "${params.protein_fdr}"
      printf 'decoy_prefix\t%s\n' "${params.decoy_prefix}"
      printf 'picked\ttrue\nrazor\ttrue\nsequential\tfalse\n'
    } > "${sample}.filter.provenance.tsv"
    """
}
