process IONQUANT_LFQ {
    tag 'ionquant-lfq'

    cpus 2
    memory '4 GB'
    time '4 h'

    publishDir "${params.outdir}/quantification", mode: 'copy', overwrite: false,
        saveAs: { name -> name == 'ionquant.reports' ? 'ionquant' : null }
    publishDir "${params.outdir}/provenance", mode: 'copy', overwrite: false,
        saveAs: { name -> name.endsWith('.ionquant.provenance.tsv') ? name : null }
    publishDir "${params.outdir}/qc", mode: 'copy', overwrite: false,
        saveAs: { name -> name.endsWith('.quantification_qc.tsv') ? name : null }

    input:
    tuple path(manifest), path(ionquant_jar), path(msfragger_ext), path(preflight_report)

    output:
    path 'ionquant.reports', emit: reports
    path 'ionquant.ionquant.provenance.tsv', emit: provenance
    path 'ionquant.quantification_qc.tsv', emit: qc

    script:
    mbr_enabled = params.ionquant_mbr.toString().toBoolean()
    mbr_value = mbr_enabled ? 1 : 0
    mbr_label = mbr_enabled ? 'on' : 'off'
    python_bin = params.python
    java_xmx = params.ionquant_xmx
    project_root = projectDir
    """
    "${python_bin}" "${project_root}/bin/verify_tool.py" \
      --tool ionquant --path "${ionquant_jar}" --expected-version 1.11.20 \
      > ionquant.version.tsv
    "${python_bin}" "${project_root}/bin/validate_ionquant_ext.py" \
      --ext "${msfragger_ext}" --output ionquant-ext.validation.tsv

    if [ "\$(basename "${msfragger_ext}")" != ext ]; then
      ln -s "\$(readlink -f "${msfragger_ext}")" ext
    fi
    mkdir -p ionquant-inputs ionquant-combined ionquant.reports/runs ionquant.reports/combined
    iq_args=''
    run_count=0
    while IFS=\$'\t' read -r sample mzml psm protein; do
      [ "\${sample}" = sample ] && continue
      mkdir -p "ionquant-inputs/\${sample}"
      ln -s "\${mzml}" "ionquant-inputs/\${sample}/\${sample}.mzML"
      cp "\${psm}" "ionquant-inputs/\${sample}/psm.tsv"
      cp "\${protein}" "ionquant-inputs/\${sample}/protein.tsv"
      iq_args="\${iq_args} --specdir ionquant-inputs/\${sample} --psm ionquant-inputs/\${sample}/psm.tsv"
      run_count=\$((run_count + 1))
    done < "${manifest}"
    normalization=1
    if [ "\${run_count}" -eq 1 ]; then normalization=0; fi

    /usr/bin/time -v -o ionquant.resource.txt \
      java -Xmx${java_xmx} -jar "${ionquant_jar}" \
      \${iq_args} --multidir ionquant-combined \
      --threads 2 --perform-ms1quant 1 --perform-isoquant 0 \
      --normalization \${normalization} --maxlfq 1 --mbr ${mbr_value} \
      --ionmobility 0 --mztol 10 --rttol 0.4 \
      --minisotopes 2 --minscans 3 --minions 1 \
      --ionfdr 0.01 --peptidefdr 0.01 --proteinfdr 0.01 \
      --intensitymode 2 --uniqueness 0 --ibaq 0 --msstats 0 \
      > ionquant.stdout.log 2> ionquant.stderr.log

    for sample_dir in ionquant-inputs/*; do
      sample=\$(basename "\${sample_dir}")
      mkdir -p "ionquant.reports/runs/\${sample}"
      for report in ion.tsv peptide.tsv protein.tsv; do
        if [ -s "\${sample_dir}/\${report}" ]; then
          cp "\${sample_dir}/\${report}" "ionquant.reports/runs/\${sample}/\${report}"
        fi
      done
    done
    for combined_file in ionquant-combined/*; do
      if [ -f "\${combined_file}" ]; then cp "\${combined_file}" ionquant.reports/combined/; fi
    done
    for report in ion peptide protein; do
      find ionquant.reports -type f -name "\${report}.tsv" -size +0c -print -quit | grep -q . || {
        echo "IonQuant error: no non-empty \${report}.tsv output was produced" >&2
        exit 5
      }
    done

    "${python_bin}" "${project_root}/bin/summarize_quantification.py" \
      --reports ionquant.reports --output ionquant.quantification_qc.tsv \
      --ionquant-version 1.11.20 --mbr ${mbr_label} --manifest "${manifest}" \
      --fasta-sha256 "${params.quant_fasta_sha256 ?: 'NA'}"
    {
      printf 'field\tvalue\n'
      printf 'ionquant_version\t1.11.20\n'
      printf 'java_xmx\t%s\n' "${java_xmx}"
      printf 'threads\t2\n'
      printf 'mbr\t%s\n' '${mbr_label}'
      printf 'normalization\t%s\n' "\${normalization}"
      printf 'maxlfq\ttrue\n'
      printf 'ionquant_jar_sha256\t%s\n' "\$(sha256sum "${ionquant_jar}" | cut -d' ' -f1)"
      printf 'execution_utc\t%s\n' "\$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    } > ionquant.ionquant.provenance.tsv
    cp ionquant.resource.txt ionquant.stdout.log ionquant.stderr.log ionquant.reports/
    """
}
