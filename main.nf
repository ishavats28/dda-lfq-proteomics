nextflow.enable.dsl = 2

include { VALIDATE_INPUTS } from './modules/local/validate_inputs'
include { MZML_QC } from './modules/local/mzml_qc'
include { VALIDATE_FASTA } from './modules/local/validate_fasta'
include { SEARCH_RESOURCE_PREFLIGHT } from './modules/local/resource_preflight'
include { MSFRAGGER_SEARCH } from './modules/local/msfragger_search'
include { PHILOSOPHER_DATABASE_PREP } from './modules/local/philosopher_database'
include { PHILOSOPHER_HUMAN_DATABASE } from './modules/local/philosopher_human_database'
include { VALIDATE_DATABASE_CACHE } from './modules/local/validate_database_cache'
include { PHILOSOPHER_PEPTIDEPROPHET } from './modules/local/philosopher_peptideprophet'
include { PHILOSOPHER_PROTEINPROPHET } from './modules/local/philosopher_proteinprophet'
include { PHILOSOPHER_FILTER } from './modules/local/philosopher_filter'
include { PHILOSOPHER_REPORT } from './modules/local/philosopher_report'
include { IDENTIFICATION_QC } from './modules/local/identification_qc'
include { CONVERT_THERMO_RAW } from './modules/local/convert_raw'
include { PHILOSOPHER_YEAST_DATABASE } from './modules/local/philosopher_yeast_database'
include { VALIDATE_QUANT_INPUTS } from './modules/local/validate_quant_inputs'
include { SEARCH_RESOURCE_PREFLIGHT as IONQUANT_RESOURCE_PREFLIGHT } from './modules/local/resource_preflight'
include { IONQUANT_LFQ } from './modules/local/ionquant'
include { BUILD_PROTEIN_MATRIX } from './modules/local/build_protein_matrix'
include { VALIDATE_ANALYSIS_DESIGN } from './modules/local/validate_design'
include { QUANTITATIVE_QC } from './modules/local/quant_qc'
include { EXPLORATORY_TECHNICAL_QC } from './modules/local/exploratory_analysis'
include { GENERATE_QUANTITATIVE_REPORT } from './modules/local/generate_report'

process PIPELINE_SMOKE_TEST {
    tag 'infrastructure-only'

    cpus 1
    memory '256 MB'

    publishDir "${params.outdir}/smoke", mode: 'copy', overwrite: false

    output:
    path 'smoke-test.txt', emit: report

    script:
    """
    printf '%s\n' \
      'DDA LFQ proteomics workflow: infrastructure smoke test passed.' \
      'This file is not a biological analysis result.' \
      > smoke-test.txt
    """
}

workflow {
    mode_count = [params.smoke, params.search_test, params.philosopher_test, params.prepare_database, params.prepare_yeast_database, params.identify, params.convert_raw, params.quantify, params.analyze]
        .count { it }
    if (mode_count > 1) {
        error 'Choose only one explicit execution mode.'
    }
    if (params.smoke && params.samplesheet) {
        error 'The --smoke mode cannot be combined with a sample sheet.'
    }

    if (params.smoke) {
        PIPELINE_SMOKE_TEST()
    } else {
        if (params.search_test && !params.samplesheet) {
            error '--search_test requires --samplesheet.'
        }
        if ((params.search_test || params.philosopher_test || params.identify) && !params.fasta) {
            error 'Scientific integration modes require --fasta.'
        }
        if (params.identify && !params.samplesheet) {
            error '--identify requires --samplesheet.'
        }
        if (params.quantify && (!params.quant_manifest || !params.ionquant_jar || !params.msfragger_ext)) {
            error '--quantify requires --quant_manifest, --ionquant_jar, and --msfragger_ext.'
        }
        if (params.analyze && (!params.combined_protein || !params.design || !params.identification_summary)) {
            error '--analyze requires --combined_protein, --design, and --identification_summary.'
        }

        if (params.convert_raw) {
            if (!params.raw || !params.raw_sample || !params.msconvert_bin) {
                error '--convert_raw requires --raw, --raw_sample, and --msconvert_bin.'
            }
            raw_file = file(params.raw, checkIfExists: true)
            CONVERT_THERMO_RAW(tuple(params.raw_sample, raw_file, params.msconvert_bin))
            mzml_inputs = CONVERT_THERMO_RAW.out.mzml
        } else if (params.samplesheet) {
            source_sheet = file(params.samplesheet, checkIfExists: true)
            validated = VALIDATE_INPUTS(source_sheet, source_sheet.parent.toString())

            mzml_inputs = validated.normalized
                .splitCsv(header: true, sep: '\t')
                .map { row -> tuple(row.sample, file(row.mzml, checkIfExists: true)) }

        }

        if (params.samplesheet || params.convert_raw) {
            MZML_QC(mzml_inputs)
        }

        if (params.search_test || params.philosopher_test || params.identify) {
            fasta_file = file(params.fasta, checkIfExists: true)
            fasta_validated = VALIDATE_FASTA(fasta_file)
        }

        if (params.prepare_database) {
            if (!params.philosopher_bin) {
                error '--prepare_database requires --philosopher_bin.'
            }
            philosopher_file = file(params.philosopher_bin)
            if (!philosopher_file.exists()) {
                error "Philosopher executable does not exist: ${params.philosopher_bin}"
            }
            cached_fasta = file("${params.database_cache_dir}/UP000005640_reviewed_contam_rev.fasta")
            cached_manifest = file("${params.database_cache_dir}/UP000005640_reviewed_contam_rev.manifest.tsv")
            if (cached_fasta.exists() != cached_manifest.exists()) {
                error 'Human database cache is incomplete: FASTA and manifest must either both exist or both be absent.'
            }
            if (cached_fasta.exists()) {
                VALIDATE_DATABASE_CACHE(tuple(cached_fasta, cached_manifest))
            } else {
                PHILOSOPHER_HUMAN_DATABASE(philosopher_file)
            }
        }

        if (params.prepare_yeast_database) {
            if (!params.philosopher_bin) {
                error '--prepare_yeast_database requires --philosopher_bin.'
            }
            philosopher_file = file(params.philosopher_bin)
            if (!philosopher_file.exists()) {
                error "Philosopher executable does not exist: ${params.philosopher_bin}"
            }
            cached_fasta = file("${params.yeast_database_cache_dir}/UP000002311_reviewed_contam_rev.fasta")
            cached_manifest = file("${params.yeast_database_cache_dir}/UP000002311_reviewed_contam_rev.manifest.tsv")
            if (cached_fasta.exists() != cached_manifest.exists()) {
                error 'Yeast database cache is incomplete: FASTA and manifest must either both exist or both be absent.'
            }
            if (cached_fasta.exists()) {
                VALIDATE_DATABASE_CACHE(tuple(cached_fasta, cached_manifest))
            } else {
                PHILOSOPHER_YEAST_DATABASE(philosopher_file)
            }
        }

        if (params.philosopher_test) {
            if (!params.philosopher_bin) {
                error '--philosopher_test requires --philosopher_bin.'
            }
            philosopher_file = file(params.philosopher_bin)
            if (!philosopher_file.exists()) {
                error "Philosopher executable does not exist: ${params.philosopher_bin}"
            }
            PHILOSOPHER_DATABASE_PREP(fasta_validated.validated, philosopher_file, params.decoy_prefix)
        }

        if (params.search_test || params.identify) {
            if (!params.msfragger_jar) {
                error 'The search mode requires --msfragger_jar pointing to the licensed MSFragger 4.4.1 JAR.'
            }
            selected_params = params.identify ? 'conf/msfragger/closed-search.params' : params.msfragger_params
            parameter_file = file(selected_params, checkIfExists: true)
            msfragger_file = file(params.msfragger_jar)
            if (!msfragger_file.exists()) {
                error "MSFragger JAR does not exist: ${params.msfragger_jar}"
            }
            preflight = SEARCH_RESOURCE_PREFLIGHT(tuple(
                params.search_min_total_gib,
                params.search_min_available_gib,
                params.search_min_free_disk_gib
            ))

            // A successful pre-QC record is an explicit dependency of search.
            // This prevents the memory-sensitive search from overlapping QC.
            search_inputs = mzml_inputs
                .join(MZML_QC.out.qc)
                .combine(fasta_validated.validated)
                .combine(preflight.report)
                .map { sample, mzml, mzml_qc, fasta, fasta_manifest, preflight_report ->
                    tuple(sample, mzml, fasta, fasta_manifest, parameter_file, msfragger_file, preflight_report)
                }

            MSFRAGGER_SEARCH(search_inputs)
        }

        if (params.identify) {
            if (!params.philosopher_bin) {
                error '--identify requires --philosopher_bin.'
            }
            philosopher_file = file(params.philosopher_bin)
            if (!philosopher_file.exists()) {
                error "Philosopher executable does not exist: ${params.philosopher_bin}"
            }

            peptideprophet_inputs = MSFRAGGER_SEARCH.out.pepxml
                .combine(fasta_validated.validated)
                .map { sample, pepxml, fasta, fasta_manifest ->
                    tuple(sample, pepxml, fasta, philosopher_file)
                }
            PHILOSOPHER_PEPTIDEPROPHET(peptideprophet_inputs)

            proteinprophet_inputs = PHILOSOPHER_PEPTIDEPROPHET.out.validated
                .map { sample, workspace, pepxml -> tuple(sample, workspace, pepxml, philosopher_file) }
            PHILOSOPHER_PROTEINPROPHET(proteinprophet_inputs)

            filter_inputs = PHILOSOPHER_PROTEINPROPHET.out.inferred
                .map { sample, workspace, pepxml, protxml ->
                    tuple(sample, workspace, pepxml, protxml, philosopher_file)
                }
            PHILOSOPHER_FILTER(filter_inputs)

            report_inputs = PHILOSOPHER_FILTER.out.filtered
                .map { sample, workspace, pepxml, protxml ->
                    tuple(sample, workspace, pepxml, protxml, philosopher_file)
                }
            PHILOSOPHER_REPORT(report_inputs)

            fasta_manifests = fasta_validated.validated.map { fasta, manifest -> manifest }
            summary_inputs = PHILOSOPHER_REPORT.out.reports
                .join(MSFRAGGER_SEARCH.out.pepxml)
                .join(MZML_QC.out.qc)
                .combine(fasta_manifests)
                .map { sample, reports, raw_pepxml, mzml_qc, fasta_manifest ->
                    tuple(sample, reports, raw_pepxml, mzml_qc, fasta_manifest)
                }
            IDENTIFICATION_QC(summary_inputs)
        }

        if (params.quantify) {
            quant_manifest = file(params.quant_manifest, checkIfExists: true)
            ionquant_file = file(params.ionquant_jar, checkIfExists: true)
            ext_directory = file(params.msfragger_ext, checkIfExists: true)
            validated_quant = VALIDATE_QUANT_INPUTS(tuple(quant_manifest, quant_manifest.parent.toString()))
            quant_preflight = IONQUANT_RESOURCE_PREFLIGHT(tuple(
                0,
                params.ionquant_min_available_gib,
                params.ionquant_min_free_disk_gib
            ))
            ionquant_inputs = validated_quant.normalized
                .combine(Channel.value(ionquant_file))
                .combine(Channel.value(ext_directory))
                .combine(quant_preflight.report)
                .map { manifest, jar, ext, preflight_report ->
                    tuple(manifest, jar, ext, preflight_report)
                }
            IONQUANT_LFQ(ionquant_inputs)
        }

        if (params.analyze) {
            combined_protein = file(params.combined_protein, checkIfExists: true)
            analysis_design = file(params.design, checkIfExists: true)
            identification_summary = file(params.identification_summary, checkIfExists: true)
            BUILD_PROTEIN_MATRIX(combined_protein)
            design_inputs = BUILD_PROTEIN_MATRIX.out.matrix
                .combine(Channel.value(analysis_design))
                .map { matrix, design -> tuple(matrix, design) }
            VALIDATE_ANALYSIS_DESIGN(design_inputs)
            quantitative_inputs = VALIDATE_ANALYSIS_DESIGN.out.validated
                .combine(Channel.value(identification_summary))
                .map { matrix, design, identification -> tuple(matrix, design, identification) }
            QUANTITATIVE_QC(quantitative_inputs)
            EXPLORATORY_TECHNICAL_QC(BUILD_PROTEIN_MATRIX.out.matrix)
            report_inputs = QUANTITATIVE_QC.out.qc
                .combine(EXPLORATORY_TECHNICAL_QC.out.analysis)
                .map { matrix, design, quant_qc, matrix_again, exploratory_qc ->
                    tuple(matrix, design, quant_qc, exploratory_qc)
                }
            GENERATE_QUANTITATIVE_REPORT(report_inputs)
        }

        if (!params.samplesheet && !params.philosopher_test && !params.prepare_database && !params.prepare_yeast_database && !params.convert_raw && !params.quantify && !params.analyze) {
            error 'Choose an execution mode: use --smoke, provide --samplesheet, or select a scientific integration mode.'
        }
    }
}
