"""Export the AsciiDoc submodel of the example package."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from excel_to_aasx.adapters.aasx.document import AasxDocumentReader
from excel_to_aasx.adapters.files import FolderDocumentWriter
from excel_to_aasx.adapters.pdf import DockerPdfCompiler
from excel_to_aasx.app.build_pdf import build_pdf
from excel_to_aasx.app.export_document import export_document
from excel_to_aasx.domain.document.render import RenderedDocument
from tests.adapters.test_aasx_reader import EXAMPLE, LIMIT
from tests.adapters.test_pdf_compiler import IMAGE, needs_docker

REFERENCE_PDF = EXAMPLE.with_name("AsciiDoc_Namur_SMT_Tech_Data_Variable_Flow_Meter-1.pdf")
PDF_LINE = (
    "The information in section `General` concerns about .. "
    "[One or two sentences explaining the section.]"
)


@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    folder = tmp_path_factory.mktemp("doc")
    return export_document(
        AasxDocumentReader(LIMIT), FolderDocumentWriter(), str(EXAMPLE), str(folder), None
    )


def test_example_exports_without_errors(exported):
    document, main_file = exported
    assert main_file.endswith("AsciiDoc_Namur_SMT_Tech_Data_Variable_Flow_Meter.adoc")
    assert not [i for i in document.issues if i.severity == "error"]
    assert document.issues == []
    uml = document.text.split(
        '[plantuml, UML_GeneralInformation, svg, id="UML_GeneralInformation"'
    )[1]
    assert 'class "GeneralInformation" as ID00000001 <<SMC>> {' in uml.split("@enduml")[0]


def test_example_text_and_assets(exported):
    document: RenderedDocument = exported[0]
    assert document.text.startswith("ifdef::env-pdf[]")
    assert PDF_LINE in document.text
    assert "%ITEM" not in document.text
    assert "\r" not in document.text
    assert "\n=== Operating conditions\n" in document.text
    assert "\n=== Type approval for legal metrology\n" in document.text
    assert document.assets["idta-spec-badge.png"].startswith(b"\x89PNG")
    assert document.assets["SMT-template-cover.svg"].startswith(b"<?xml")
    assert document.assets["DejaVuSansMono.ttf"][:4] == b"\x00\x01\x00\x00"
    assert len(document.assets) == 18


def test_reader_needs_asciidoc_submodel():
    with pytest.raises(ValueError, match="no submodel 'Nope'"):
        AasxDocumentReader(LIMIT).read(str(EXAMPLE), "Nope")


def test_example_tables(exported):
    document: RenderedDocument = exported[0]
    assert document.text.count("\n// Table generated from ") == 25
    table4 = document.text.split('id="Table_Submodel"', 1)[1].split("|===", 2)[1]
    assert "NamurTechnicalDataVariableAreaFlowMeter" in table4
    assert (
        "supplementalSemanticId(s):  +\nhttps://admin-shell.io/idta/SubmodelTemplate/TechnicalData/2/0"
        in table4
    )
    assert table4.count("[SMC]") + table4.count("[SML]") == 3
    general = document.text.split('id="Table_GeneralInformation"', 1)[1].split("\n|===\n", 2)[1]
    assert "legally valid designation of the natural or judicial person" in general
    assert 'cols="15%,45%,30%,10%"' in document.text  # Table_ProductClassification columnWidths


@needs_docker
def test_example_builds_a_39_page_pdf(tmp_path):
    document, pdf = build_pdf(
        AasxDocumentReader(LIMIT), FolderDocumentWriter(), DockerPdfCompiler(IMAGE, 300),
        str(EXAMPLE), str(tmp_path), None,
    )  # fmt: skip
    data = Path(pdf).read_bytes()
    assert data.startswith(b"%PDF")
    assert b"/Count 39" in data
    if shutil.which("pdftotext"):
        assert _words(pdf) == _words(str(REFERENCE_PDF))
    assert not [i for i in document.issues if i.severity == "error"]


def _words(pdf: str) -> list[str]:
    text = subprocess.run(["pdftotext", pdf, "-"], capture_output=True, text=True, check=True)
    return re.findall(r"\w+", text.stdout)
