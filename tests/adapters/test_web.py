import datetime
import io
import os
import time
import zipfile
from functools import partial
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from excel_to_aasx.adapters.aasx import AasxPackageWriter
from excel_to_aasx.adapters.aasx.document import AasxDocumentReader
from excel_to_aasx.adapters.aasx.document_submodel import AasxDocumentEditor
from excel_to_aasx.adapters.excel import ExcelSheetReader
from excel_to_aasx.adapters.files import FolderDocumentWriter
from excel_to_aasx.adapters.templates import load_frame
from excel_to_aasx.adapters.web import WebLimits, WebServices, Workspaces, create_app
from excel_to_aasx.app.add_document import add_document, has_document
from excel_to_aasx.app.export_document import export_document
from excel_to_aasx.app.import_workbook import import_workbook
from excel_to_aasx.app.open_upload import open_upload
from tests.adapters.test_aasx_reader import LIMIT
from tests.demo import DEMO



def _fake_pdf(adoc: str) -> tuple[str, list[str]]:
    target = Path(adoc).with_suffix(".pdf")
    target.write_bytes(b"%PDF-1.4 " + Path(adoc).read_bytes()[:20])
    return str(target), ["asciidoctor: WARNING: fake"]


def _add_document(editor, source, target, submodel):
    return add_document(editor, load_frame, source, target, submodel, datetime.date(2026, 11, 19))


def _app(tmp_path, compile_pdf=_fake_pdf, **limits):
    editor = AasxDocumentEditor(LIMIT)
    import_ = partial(import_workbook, ExcelSheetReader(LIMIT), AasxPackageWriter())
    add = partial(_add_document, editor)
    export = partial(export_document, AasxDocumentReader(LIMIT), FolderDocumentWriter())
    opener = partial(open_upload, import_, add, partial(has_document, editor), export)
    workspaces = Workspaces(tmp_path / "ws", idle_seconds=60, max_count=limits.pop("max_count", 10))
    app = create_app(WebServices(opener, compile_pdf), workspaces, WebLimits(**limits))
    return TestClient(app), workspaces


@pytest.fixture
def client(tmp_path):
    return _app(tmp_path)[0]


def _upload(client, path: Path, name: str | None = None):
    with path.open("rb") as handle:
        return client.post("/api/workspaces", files={"file": (name or path.name, handle)})


def test_index_and_security_headers(client):
    response = client.get("/")
    assert response.status_code == 200 and "excel-to-aasx" in response.text
    assert "script-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["x-frame-options"] == "DENY"
    assert client.get("/static/vendor/codemirror.js").status_code == 200
    assert 'id="try-example"' in response.text
    nonce = response.text.split('name="csp-nonce" content="')[1].split('"')[0]
    assert len(nonce) > 16
    assert f"style-src 'self' 'nonce-{nonce}'" in response.headers["content-security-policy"]
    assert nonce not in client.get("/").text  # fresh per request


def test_home_page_demo_workbook_imports_cleanly(client, tmp_path):
    response = client.get("/static/examples/demo-level-sensor.xlsx")
    assert response.status_code == 200
    demo = tmp_path / "demo.xlsx"
    demo.write_bytes(response.content)
    body = _upload(client, demo).json()
    assert body["issues"] == [] and body["document"]["text"]


def test_excel_upload_gives_package_and_document(client):
    response = _upload(client, DEMO)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["kind"] == "xlsx"
    assert body["document"]["name"] == "AsciiDoc_DemoLevelSensor.adoc"
    assert "Table for Submodel DemoLevelSensor" in body["document"]["text"]
    package = client.get(f"/api/workspaces/{body['id']}/package.aasx")
    assert package.status_code == 200 and package.content[:2] == b"PK"


def test_aasx_with_document_is_used_as_is(client, tmp_path):
    first = _upload(client, DEMO).json()
    package = tmp_path / "with-document.aasx"
    package.write_bytes(client.get(f"/api/workspaces/{first['id']}/package.aasx").content)
    body = _upload(client, package).json()
    assert body["kind"] == "aasx"
    assert body["document"] == first["document"]
    asset = client.get(f"/api/workspaces/{body['id']}/files/idta-spec-badge.png")
    assert asset.status_code == 200 and asset.content.startswith(b"\x89PNG")
    assert asset.headers["content-security-policy"].startswith("sandbox")


def test_edit_save_zip_and_pdf(client):
    workspace = _upload(client, DEMO).json()["id"]
    assert (
        client.put(f"/api/workspaces/{workspace}/document", content="= Edited\n").status_code == 204
    )
    archive = zipfile.ZipFile(
        io.BytesIO(client.get(f"/api/workspaces/{workspace}/document.zip").content)
    )
    main = next(n for n in archive.namelist() if n.endswith(".adoc"))
    assert archive.read(main) == b"= Edited\n"
    assert "my-theme.yml" in archive.namelist()
    pdf = client.post(f"/api/workspaces/{workspace}/pdf", content="= For PDF\n")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-1.4 = For PDF")
    assert pdf.headers["x-build-messages"] == '["asciidoctor: WARNING: fake"]'


def test_rejects_bad_uploads(client, tmp_path):
    other = tmp_path / "x.txt"
    other.write_text("hello")
    assert _upload(client, other).status_code == 400
    broken = tmp_path / "broken.xlsx"
    broken.write_text("not a workbook")
    response = _upload(client, broken)
    assert response.status_code == 400 and "not a readable" in response.json()["detail"]


def test_upload_and_document_size_limits(tmp_path):
    client, _ = _app(tmp_path, max_upload_bytes=1000, max_document_bytes=10)
    assert _upload(client, DEMO).status_code == 413
    client2, _ = _app(tmp_path / "2", max_document_bytes=10)
    workspace = _upload(client2, DEMO).json()["id"]
    assert client2.put(f"/api/workspaces/{workspace}/document", content="x" * 11).status_code == 413


def test_unknown_or_malformed_workspace_and_file_names(client):
    assert client.get("/api/workspaces/" + "0" * 32 + "/package.aasx").status_code == 404
    assert client.get("/api/workspaces/../package.aasx").status_code == 404
    workspace = _upload(client, DEMO).json()["id"]
    for name in ("..%2Fmeta.json", ".hidden", "missing.png"):
        assert client.get(f"/api/workspaces/{workspace}/files/{name}").status_code == 404


def test_session_cap_and_delete(tmp_path):
    client, workspaces = _app(tmp_path, max_count=1)
    workspace = _upload(client, DEMO).json()["id"]
    assert _upload(client, DEMO).status_code == 503
    assert client.delete(f"/api/workspaces/{workspace}").status_code == 204
    assert _upload(client, DEMO).status_code == 200


def test_idle_workspaces_expire(tmp_path):
    workspaces = Workspaces(tmp_path / "ws", idle_seconds=1, max_count=5)
    workspace_id, folder = workspaces.create()
    old = time.time() - 10
    os.utime(folder, (old, old))
    assert workspaces.get(workspace_id) is None
    assert not folder.exists()


def test_pdf_failure_is_reported(tmp_path):
    def failing(_adoc):
        raise ValueError("boom")

    client, _ = _app(tmp_path, compile_pdf=failing)
    workspace = _upload(client, DEMO).json()["id"]
    response = client.post(f"/api/workspaces/{workspace}/pdf", content="= x")
    assert response.status_code == 422 and "boom" in response.json()["detail"]


def test_body_limit_without_declared_length(tmp_path):
    client, _ = _app(tmp_path, max_upload_bytes=1000)

    def chunks():
        yield (
            b'--b\r\nContent-Disposition: form-data; name="file"; filename="a.xlsx"\r\n'
            b"Content-Type: application/octet-stream\r\n\r\n"
        )
        for _ in range(100):
            yield b"x" * 1000
        yield b"\r\n--b--\r\n"

    response = client.post(
        "/api/workspaces",
        content=chunks(),
        headers={"content-type": "multipart/form-data; boundary=b"},
    )
    assert response.status_code == 413


def test_symlinks_are_never_served_or_zipped(tmp_path):
    client, workspaces = _app(tmp_path)
    workspace = _upload(client, DEMO).json()["id"]
    folder = workspaces.get(workspace)
    assert folder is not None
    secret = tmp_path / "secret.txt"
    secret.write_text("host secret")
    (folder / "doc" / "leak.txt").symlink_to(secret)
    assert client.get(f"/api/workspaces/{workspace}/files/leak.txt").status_code == 404
    archive = zipfile.ZipFile(
        io.BytesIO(client.get(f"/api/workspaces/{workspace}/document.zip").content)
    )
    assert "leak.txt" not in archive.namelist()


def test_workspaces_are_private(tmp_path):
    _, workspaces = _app(tmp_path)
    workspace_id, folder = workspaces.create()
    assert folder.stat().st_mode & 0o077 == 0
    assert folder.parent.stat().st_mode & 0o077 == 0
