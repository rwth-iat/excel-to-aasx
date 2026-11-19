import pytest

from excel_to_aasx.adapters.files import FolderDocumentWriter
from excel_to_aasx.domain.document.render import RenderedDocument


def test_writes_document_and_assets(tmp_path):
    document = RenderedDocument("d.adoc", "text\n", {"a.png": b"png"})
    main = FolderDocumentWriter().write(str(tmp_path / "out"), document)
    assert (tmp_path / "out" / "d.adoc").read_text() == "text\n"
    assert (tmp_path / "out" / "a.png").read_bytes() == b"png"
    assert main == str((tmp_path / "out" / "d.adoc").resolve())


def test_refuses_names_outside_folder(tmp_path):
    document = RenderedDocument("d.adoc", "", {"../evil": b"x"})
    with pytest.raises(ValueError, match="outside"):
        FolderDocumentWriter().write(str(tmp_path / "out"), document)
    assert not (tmp_path / "evil").exists()
