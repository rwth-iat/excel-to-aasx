"""Export the AsciiDoc submodel of the example package."""

import pytest

from excel_to_aasx.adapters.aasx.document import AasxDocumentReader
from excel_to_aasx.adapters.files import FolderDocumentWriter
from excel_to_aasx.app.export_document import export_document
from excel_to_aasx.domain.document.render import RenderedDocument
from tests.adapters.test_aasx_reader import EXAMPLE, LIMIT

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
    assert {i.message for i in document.issues} == {
        "table generation is not implemented yet",
        "UML diagram generation is not implemented yet",
    }


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
