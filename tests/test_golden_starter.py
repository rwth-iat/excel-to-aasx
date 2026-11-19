"""Excel -> AASX -> starter document -> AsciiDoc, on the example workbook (ADR 0008)."""

import datetime
import zipfile

import pytest

from excel_to_aasx.adapters.aasx import AasxPackageReader, AasxPackageWriter
from excel_to_aasx.adapters.aasx.document import AasxDocumentReader
from excel_to_aasx.adapters.aasx.document_submodel import AasxDocumentEditor
from excel_to_aasx.adapters.aasx.package import load_environment
from excel_to_aasx.adapters.excel import ExcelSheetReader
from excel_to_aasx.adapters.files import FolderDocumentWriter
from excel_to_aasx.adapters.templates import load_frame
from excel_to_aasx.app.add_document import add_document
from excel_to_aasx.app.compare_packages import compare_packages
from excel_to_aasx.app.export_document import export_document
from excel_to_aasx.app.import_workbook import import_workbook
from excel_to_aasx.domain.report import Mount
from tests.adapters.test_aasx_reader import LIMIT
from tests.adapters.test_excel_reader import WORKBOOK

TODAY = datetime.date(2026, 11, 19)


@pytest.fixture(scope="module")
def packages(tmp_path_factory):
    folder = tmp_path_factory.mktemp("starter")
    imported, with_doc = folder / "import.aasx", folder / "with-doc.aasx"
    import_workbook(ExcelSheetReader(LIMIT), AasxPackageWriter(), str(WORKBOOK), str(imported))
    editor = AasxDocumentEditor(LIMIT)
    id_short = add_document(editor, load_frame, str(imported), str(with_doc), None, TODAY)
    return imported, with_doc, id_short, folder


def test_document_submodel_is_added_and_valid(packages):
    imported, with_doc, id_short, _ = packages
    assert id_short == "AsciiDoc_NAMUR_SMT_FloatTypeFowMeter"
    environment = load_environment(str(with_doc), LIMIT)
    assert [s.id_short for s in environment.submodels or []] == [
        "NAMUR_SMT_FloatTypeFowMeter",
        id_short,
    ]
    shells = environment.asset_administration_shells or []
    assert len(shells[0].submodels or []) == 2
    import aas_core3_1.verification as verification

    paths = [str(e.path) for e in verification.verify(environment)]
    assert not [p for p in paths if ".submodels[1]" in p]  # the new submodel is valid
    with zipfile.ZipFile(imported) as a, zipfile.ZipFile(with_doc) as b:
        assert a.namelist() == b.namelist()


def test_data_submodel_is_unchanged(packages):
    imported, with_doc, _, _ = packages
    report = compare_packages(
        AasxPackageReader(LIMIT),
        str(imported),
        str(with_doc),
        Mount("NAMUR_SMT_FloatTypeFowMeter", ""),
    )
    assert report.differences == ()


def test_starter_document_exports_cleanly(packages):
    _, with_doc, _, folder = packages
    document, _ = export_document(
        AasxDocumentReader(LIMIT), FolderDocumentWriter(), str(with_doc), str(folder / "doc"), None
    )
    assert document.issues == []
    assert document.text.count("\n// Table generated from ") == 20  # submodel + 19 collections
    assert "[plantuml, UML_Submodel, svg" in document.text
    assert "= [IDTA number] : NAMUR_SMT_FloatTypeFowMeter" in document.text
    assert set(document.assets) >= {"my-theme.yml", "SMT-template-cover.svg", "DejaVuSansMono.ttf"}
    assert document.assets["SMT-template-cover.svg"].startswith(b"<?xml")  # base64 round trip


def test_second_document_is_refused(packages):
    _, with_doc, _, folder = packages
    with pytest.raises(ValueError, match="already has an AsciiDoc"):
        add_document(
            AasxDocumentEditor(LIMIT),
            load_frame,
            str(with_doc),
            str(folder / "x.aasx"),
            None,
            TODAY,
        )


def test_unknown_template():
    with pytest.raises(ValueError, match="unknown document template"):
        load_frame("../etc")
