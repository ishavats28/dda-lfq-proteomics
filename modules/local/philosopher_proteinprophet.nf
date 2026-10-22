process PHILOSOPHER_PROTEINPROPHET {
    tag sample

    cpus 1
    memory '2 GB'
    time '2 h'

    publishDir "${params.outdir}/provenance", mode: 'copy', overwrite: false,
        saveAs: { name -> name.endsWith('.proteinprophet.provenance.tsv') ? name : null }

    input:
    tuple val(sample), path(previous_workspace), path(peptide_xml), path(philosopher_bin)

    output:
    tuple val(sample), path("${sample}.proteinprophet.workspace"), path('combined.pep.xml'), path('combined.prot.xml'), emit: inferred
    tuple val(sample), path("${sample}.proteinprophet.provenance.tsv"), emit: provenance

    script:
    """
    test -s "${peptide_xml}" || { echo 'ProteinProphet error: PeptideProphet output is absent or empty' >&2; exit 4; }
    cp -a "${previous_workspace}" "${sample}.proteinprophet.workspace"
    cp "${peptide_xml}" "${sample}.proteinprophet.workspace/combined.pep.xml"
    tool_path=\$(readlink -f "${philosopher_bin}")
    cd "${sample}.proteinprophet.workspace"
    /usr/bin/time -v -o proteinprophet.resource.txt \
      "\${tool_path}" proteinprophet --output combined combined.pep.xml \
      > proteinprophet.stdout.log 2> proteinprophet.stderr.log
    test -s combined.prot.xml || { echo 'ProteinProphet error: combined.prot.xml was not produced' >&2; exit 5; }
    cd ..
    cp "${sample}.proteinprophet.workspace/combined.pep.xml" combined.pep.xml
    cp "${sample}.proteinprophet.workspace/combined.prot.xml" combined.prot.xml
    printf 'field\tvalue\nphilosopher_version\t5.1.0\noutput\tcombined.prot.xml\n' \
      > "${sample}.proteinprophet.provenance.tsv"
    """
}
