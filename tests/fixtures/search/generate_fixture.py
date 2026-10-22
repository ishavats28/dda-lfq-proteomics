#!/usr/bin/env python3
"""Generate the deterministic, non-biological MSFragger integration mzML."""

from __future__ import annotations

import base64
import struct
import xml.etree.ElementTree as ET
from pathlib import Path


PEPTIDE = "ACDEFGHILMNPQRSTK"
PROTON = 1.007276466621
WATER = 18.01056468403
CARBAMIDOMETHYL_C = 57.021463735
AA_MASS = {
    "A": 71.037113805,
    "C": 103.009184505,
    "D": 115.026943065,
    "E": 129.042593135,
    "F": 147.068413945,
    "G": 57.021463735,
    "H": 137.058911875,
    "I": 113.084063975,
    "K": 128.094963015,
    "L": 113.084063975,
    "M": 131.040484645,
    "N": 114.042927470,
    "P": 97.052763875,
    "Q": 128.058577540,
    "R": 156.101111050,
    "S": 87.032028435,
    "T": 101.047678505,
    "V": 99.068413945,
    "W": 186.079312980,
    "Y": 163.063328575,
}


NS = "http://psi.hupo.org/ms/mzml"
ET.register_namespace("", NS)


def q(tag: str) -> str:
    return f"{{{NS}}}{tag}"


def residue_mass(residue: str) -> float:
    return AA_MASS[residue] + (CARBAMIDOMETHYL_C if residue == "C" else 0.0)


def binary(values: list[float]) -> str:
    packed = struct.pack("<" + "d" * len(values), *values)
    return base64.b64encode(packed).decode("ascii")


def cv(parent: ET.Element, accession: str, name: str, value: str | None = None, **units: str) -> None:
    attributes = {"cvRef": "UO" if accession.startswith("UO:") else "MS", "accession": accession, "name": name}
    if value is not None:
        attributes["value"] = value
    attributes.update(units)
    ET.SubElement(parent, q("cvParam"), attributes)


def add_arrays(spectrum: ET.Element, mz_values: list[float], intensities: list[float]) -> None:
    arrays = ET.SubElement(spectrum, q("binaryDataArrayList"), {"count": "2"})
    for accession, name, values, unit_accession, unit_name in (
        ("MS:1000514", "m/z array", mz_values, "MS:1000040", "m/z"),
        ("MS:1000515", "intensity array", intensities, "MS:1000131", "number of detector counts"),
    ):
        encoded = binary(values)
        array = ET.SubElement(arrays, q("binaryDataArray"), {"encodedLength": str(len(encoded))})
        cv(array, "MS:1000523", "64-bit float")
        cv(array, "MS:1000576", "no compression")
        cv(array, accession, name, unitCvRef="MS", unitAccession=unit_accession, unitName=unit_name)
        ET.SubElement(array, q("binary")).text = encoded


def theoretical_fragments() -> list[float]:
    masses = [residue_mass(residue) for residue in PEPTIDE]
    fragments: list[float] = []
    for cut in range(1, len(PEPTIDE)):
        fragments.append(sum(masses[:cut]) + PROTON)
        fragments.append(sum(masses[cut:]) + WATER + PROTON)
    return sorted(fragments)


def build_document() -> tuple[ET.ElementTree, float, list[float]]:
    peptide_mass = sum(residue_mass(residue) for residue in PEPTIDE) + WATER
    precursor_mz = (peptide_mass + 2 * PROTON) / 2
    fragments = theoretical_fragments()
    noise = [111.1111, 222.2222, 333.3333, 444.4444, 555.5555, 777.7777]
    peaks = sorted([(mz, 1000.0 - index * 20.0) for index, mz in enumerate(fragments)] + [(mz, 75.0) for mz in noise])

    root = ET.Element(q("mzML"), {"version": "1.1.0", "id": "synthetic_search_fixture"})
    cv_list = ET.SubElement(root, q("cvList"), {"count": "2"})
    ET.SubElement(cv_list, q("cv"), {"id": "MS", "fullName": "Proteomics Standards Initiative Mass Spectrometry Ontology", "version": "4.1.0", "URI": "https://raw.githubusercontent.com/HUPO-PSI/psi-ms-CV/master/psi-ms.obo"})
    ET.SubElement(cv_list, q("cv"), {"id": "UO", "fullName": "Unit Ontology", "version": "1.0", "URI": "http://purl.obolibrary.org/obo/uo.obo"})
    description = ET.SubElement(root, q("fileDescription"))
    content = ET.SubElement(description, q("fileContent"))
    cv(content, "MS:1000580", "MSn spectrum")
    software_list = ET.SubElement(root, q("softwareList"), {"count": "1"})
    software = ET.SubElement(software_list, q("software"), {"id": "synthetic_fixture_generator", "version": "1"})
    cv(software, "MS:1000799", "custom unreleased software tool")
    instruments = ET.SubElement(root, q("instrumentConfigurationList"), {"count": "1"})
    instrument = ET.SubElement(instruments, q("instrumentConfiguration"), {"id": "IC1"})
    components = ET.SubElement(instrument, q("componentList"), {"count": "3"})
    source = ET.SubElement(components, q("source"), {"order": "1"}); cv(source, "MS:1000398", "nanoelectrospray")
    analyzer = ET.SubElement(components, q("analyzer"), {"order": "2"}); cv(analyzer, "MS:1000484", "orbitrap")
    detector = ET.SubElement(components, q("detector"), {"order": "3"}); cv(detector, "MS:1000253", "electron multiplier")
    processing_list = ET.SubElement(root, q("dataProcessingList"), {"count": "1"})
    processing = ET.SubElement(processing_list, q("dataProcessing"), {"id": "DP1"})
    method = ET.SubElement(processing, q("processingMethod"), {"order": "1", "softwareRef": "synthetic_fixture_generator"})
    cv(method, "MS:1000544", "Conversion to mzML")
    run = ET.SubElement(root, q("run"), {"id": "synthetic_search_run", "defaultInstrumentConfigurationRef": "IC1"})
    spectra = ET.SubElement(run, q("spectrumList"), {"count": "2", "defaultDataProcessingRef": "DP1"})

    ms1_mz = [precursor_mz - 0.5, precursor_mz, precursor_mz + 0.5017]
    ms1 = ET.SubElement(spectra, q("spectrum"), {"index": "0", "id": "scan=1", "defaultArrayLength": str(len(ms1_mz))})
    cv(ms1, "MS:1000511", "ms level", "1"); cv(ms1, "MS:1000127", "centroid spectrum")
    scans = ET.SubElement(ms1, q("scanList"), {"count": "1"}); scan = ET.SubElement(scans, q("scan"))
    cv(scan, "MS:1000016", "scan start time", "1.0", unitCvRef="UO", unitAccession="UO:0000031", unitName="minute")
    add_arrays(ms1, ms1_mz, [100.0, 10000.0, 1200.0])

    mz_values = [value[0] for value in peaks]
    intensity_values = [value[1] for value in peaks]
    ms2 = ET.SubElement(spectra, q("spectrum"), {"index": "1", "id": "scan=2", "defaultArrayLength": str(len(mz_values))})
    cv(ms2, "MS:1000511", "ms level", "2"); cv(ms2, "MS:1000127", "centroid spectrum")
    scans = ET.SubElement(ms2, q("scanList"), {"count": "1"}); scan = ET.SubElement(scans, q("scan"))
    cv(scan, "MS:1000016", "scan start time", "2.0", unitCvRef="UO", unitAccession="UO:0000031", unitName="minute")
    precursor_list = ET.SubElement(ms2, q("precursorList"), {"count": "1"})
    precursor = ET.SubElement(precursor_list, q("precursor"), {"spectrumRef": "scan=1"})
    isolation = ET.SubElement(precursor, q("isolationWindow"))
    cv(isolation, "MS:1000827", "isolation window target m/z", f"{precursor_mz:.8f}", unitCvRef="MS", unitAccession="MS:1000040", unitName="m/z")
    cv(isolation, "MS:1000828", "isolation window lower offset", "0.7", unitCvRef="MS", unitAccession="MS:1000040", unitName="m/z")
    cv(isolation, "MS:1000829", "isolation window upper offset", "0.7", unitCvRef="MS", unitAccession="MS:1000040", unitName="m/z")
    ions = ET.SubElement(precursor, q("selectedIonList"), {"count": "1"}); ion = ET.SubElement(ions, q("selectedIon"))
    cv(ion, "MS:1000744", "selected ion m/z", f"{precursor_mz:.8f}", unitCvRef="MS", unitAccession="MS:1000040", unitName="m/z")
    cv(ion, "MS:1000041", "charge state", "2")
    activation = ET.SubElement(precursor, q("activation")); cv(activation, "MS:1000422", "beam-type collision-induced dissociation")
    add_arrays(ms2, mz_values, intensity_values)
    return ET.ElementTree(root), precursor_mz, fragments


def main() -> None:
    tree, precursor_mz, fragments = build_document()
    output = Path(__file__).with_name("synthetic_search.mzML")
    ET.indent(tree, space="  ")
    tree.write(output, encoding="utf-8", xml_declaration=True)
    print(f"wrote {output.name}: peptide={PEPTIDE}, precursor_mz={precursor_mz:.8f}, fragments={len(fragments)}")


if __name__ == "__main__":
    main()
