process IDENTIFICATION_QC {
    tag sample

    cpus 1
    memory '256 MB'
    time '10 min'

    publishDir "${params.outdir}/qc", mode: 'copy', overwrite: false

    input:
    tuple val(sample), path(reports), path(raw_pepxml), path(mzml_qc), path(fasta_manifest)

    output:
    tuple val(sample), path("${sample}.identification_qc.tsv"), emit: summary

    script:
    """
    "${params.python}" "${projectDir}/bin/summarize_identifications.py" \
      --sample "${sample}" \
      --mzml-qc "${mzml_qc}" \
      --raw-pepxml "${raw_pepxml}" \
      --psm "${reports}/psm.tsv" \
      --peptide "${reports}/peptide.tsv" \
      --protein "${reports}/protein.tsv" \
      --decoy-prefix "${params.decoy_prefix}" \
      --psm-fdr "${params.psm_fdr}" \
      --peptide-fdr "${params.peptide_fdr}" \
      --protein-fdr "${params.protein_fdr}" \
      --database-manifest "${fasta_manifest}" \
      --output "${sample}.identification_qc.tsv"
    """
}
