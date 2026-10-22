process PHILOSOPHER_REPORT {
    tag sample

    cpus 1
    memory '1 GB'
    time '1 h'

    publishDir "${params.outdir}/identification", mode: 'copy', overwrite: false,
        saveAs: { name -> name == "${sample}.reports" ? sample : null }

    input:
    tuple val(sample), path(previous_workspace), path(peptide_xml), path(protein_xml), path(philosopher_bin)

    output:
    tuple val(sample), path("${sample}.reports"), emit: reports

    script:
    """
    cp -a "${previous_workspace}" "${sample}.report.workspace"
    cp "${peptide_xml}" "${sample}.report.workspace/combined.pep.xml"
    cp "${protein_xml}" "${sample}.report.workspace/combined.prot.xml"
    tool_path=\$(readlink -f "${philosopher_bin}")
    cd "${sample}.report.workspace"
    /usr/bin/time -v -o report.resource.txt \
      "\${tool_path}" report > report.stdout.log 2> report.stderr.log
    for report in psm.tsv peptide.tsv protein.tsv; do
      test -s "\${report}" || { echo "Philosopher report error: \${report} was not produced" >&2; exit 5; }
    done
    cd ..
    mkdir "${sample}.reports"
    cp "${sample}.report.workspace/psm.tsv" "${sample}.reports/psm.tsv"
    cp "${sample}.report.workspace/peptide.tsv" "${sample}.reports/peptide.tsv"
    cp "${sample}.report.workspace/protein.tsv" "${sample}.reports/protein.tsv"
    cp "${sample}.report.workspace/report.resource.txt" "${sample}.reports/report.resource.txt"
    cp "${sample}.report.workspace/report.stdout.log" "${sample}.reports/report.stdout.log"
    cp "${sample}.report.workspace/report.stderr.log" "${sample}.reports/report.stderr.log"
    """
}
