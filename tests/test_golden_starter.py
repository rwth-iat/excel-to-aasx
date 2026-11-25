"""Demo workbook -> AASX -> starter document -> AsciiDoc -> PDF (ADR 0008)."""

import datetime
import zipfile
from pathlib import Path

import pytest

from excel_to_aasx.adapters.aasx import AasxPackageReader, AasxPackageWriter
from excel_to_aasx.adapters.aasx.document import AasxDocumentReader
from excel_to_aasx.adapters.aasx.document_submodel import AasxDocumentEditor
from excel_to_aasx.adapters.aasx.package import load_environment
from excel_to_aasx.adapters.excel import ExcelSheetReader
from excel_to_aasx.adapters.files import FolderDocumentWriter
from excel_to_aasx.adapters.pdf import DockerPdfCompiler
from excel_to_aasx.adapters.templates import load_frame
from excel_to_aasx.app.add_document import add_document
from excel_to_aasx.app.build_pdf import build_pdf
from excel_to_aasx.app.compare_packages import compare_packages
from excel_to_aasx.app.export_document import export_document
from excel_to_aasx.app.import_workbook import import_workbook
from excel_to_aasx.domain.report import Mount
from tests.adapters.test_pdf_compiler import IMAGE, needs_docker
from tests.demo import DEMO, LIMIT

TODAY = datetime.date(2026, 11, 19)


@pytest.fixture(scope="module")
def packages(tmp_path_factory):
    folder = tmp_path_factory.mktemp("starter")
    imported, with_doc = folder / "import.aasx", folder / "with-doc.aasx"
    import_workbook(ExcelSheetReader(LIMIT), AasxPackageWriter(), str(DEMO), str(imported))
    editor = AasxDocumentEditor(LIMIT)
    id_short = add_document(editor, load_frame, str(imported), str(with_doc), None, TODAY)
    return imported, with_doc, id_short, folder


def test_document_submodel_is_added_and_valid(packages):
    imported, with_doc, id_short, _ = packages
    assert id_short == "AsciiDoc_DemoLevelSensor"
    environment = load_environment(str(with_doc), LIMIT)
    assert [s.id_short for s in environment.submodels or []] == [
        "DemoLevelSensor",
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
        Mount("DemoLevelSensor", ""),
    )
    assert report.differences == ()


def test_starter_document_exports_cleanly(packages):
    _, with_doc, _, folder = packages
    document, _ = export_document(
        AasxDocumentReader(LIMIT), FolderDocumentWriter(), str(with_doc), str(folder / "doc"), None
    )
    assert document.issues == []
    assert document.text.startswith("ifdef::env-pdf[]")
    assert "%ITEM" not in document.text and "\r" not in document.text
    assert document.text.count("\n// Table generated from ") == 5  # submodel + 4 collections
    assert "[plantuml, UML_Submodel, svg" in document.text
    assert "= [IDTA number] : DemoLevelSensor" in document.text
    assert "\n=== SubmodelElements of MeasuringRange\n" in document.text
    assert set(document.assets) >= {"my-theme.yml", "SMT-template-cover.svg", "DejaVuSansMono.ttf"}
    assert document.assets["SMT-template-cover.svg"].startswith(b"<?xml")  # base64 round trip
    assert document.assets["idta-spec-badge.png"].startswith(b"\x89PNG")
    assert document.assets["DejaVuSansMono.ttf"][:4] == b"\x00\x01\x00\x00"


def test_reader_needs_asciidoc_submodel(packages):
    _, with_doc, _, _ = packages
    with pytest.raises(ValueError, match="no submodel 'Nope'"):
        AasxDocumentReader(LIMIT).read(str(with_doc), "Nope")


@needs_docker
def test_starter_document_builds_a_pdf(packages, tmp_path):
    _, with_doc, _, _ = packages
    document, pdf = build_pdf(
        AasxDocumentReader(LIMIT), FolderDocumentWriter(), DockerPdfCompiler(IMAGE, 300),
        str(with_doc), str(tmp_path), None,
    )  # fmt: skip
    assert Path(pdf).read_bytes().startswith(b"%PDF")
    assert not [i for i in document.issues if i.severity == "error"]


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
