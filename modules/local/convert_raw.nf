process CONVERT_THERMO_RAW {
    tag sample

    cpus 1
    memory '512 MB'
    time '4 h'

    publishDir "${params.outdir}/conversion/mzml", mode: 'copy', overwrite: false,
        saveAs: { name -> name.endsWith('.mzML') ? name : null }
    publishDir "${params.outdir}/conversion/provenance", mode: 'copy', overwrite: false,
        saveAs: { name -> name.endsWith('.conversion.tsv') ? name : null }
    publishDir "${params.outdir}/conversion/logs", mode: 'copy', overwrite: false,
        saveAs: { name -> name.endsWith('.log') ? name : null }

    input:
    tuple val(sample), path(raw), val(msconvert_bin)

    output:
    tuple val(sample), path("${sample}.mzML"), emit: mzml
    tuple val(sample), path("${sample}.conversion.tsv"), emit: provenance
    tuple val(sample), path("${sample}.msconvert.stdout.log"), path("${sample}.msconvert.stderr.log"), emit: logs

    script:
    """
    /usr/bin/time -v "${params.python}" "${projectDir}/bin/convert_thermo_raw.py" \
      --sample "${sample}" \
      --input "${raw}" \
      --msconvert "${msconvert_bin}" \
      --output-dir . \
      --provenance "${sample}.conversion.tsv" \
      --stdout-log "${sample}.msconvert.stdout.log" \
      --stderr-log "${sample}.msconvert.stderr.log"
    """
}
