"""The builder service (builder/server.py) without asciidoctor: checks and wire format."""

import importlib.util
import io
import json
import threading
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from excel_to_aasx.adapters.pdf.remote import RemotePdfCompiler

SPEC = importlib.util.spec_from_file_location(
    "builder_server", Path(__file__).parents[1] / "builder" / "server.py"
)
assert SPEC and SPEC.loader
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)


def _zip(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return buffer.getvalue()


@pytest.mark.parametrize(
    "name", ["../evil.adoc", "/abs.adoc", "sub/dir.adoc", ".hidden", "a b.adoc"]
)
def test_unpack_rejects_paths_and_odd_names(tmp_path, name):
    with pytest.raises(server.BuildError, match="invalid file name"):
        server.unpack(_zip({name: b"x"}), tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_unpack_limits(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "MAX_FILES", 2)
    with pytest.raises(server.BuildError, match="more than 2 files"):
        server.unpack(_zip({"a": b"", "b": b"", "c": b""}), tmp_path)
    monkeypatch.setattr(server, "MAX_UNPACKED_BYTES", 10)
    with pytest.raises(server.BuildError, match="too large"):
        server.unpack(_zip({"a": b"x" * 11}), tmp_path)
    with pytest.raises(server.BuildError, match="not a ZIP"):
        server.unpack(b"nope", tmp_path)


def test_theme_fonts_are_relocated(tmp_path):
    (tmp_path / "my-theme.yml").write_text("normal: /documents/DejaVuSansMono.ttf\n")
    server._relocate_theme(tmp_path)
    assert (tmp_path / "my-theme.yml").read_text() == f"normal: {tmp_path}/DejaVuSansMono.ttf\n"


def test_command_is_secure_and_uses_our_extension(tmp_path):
    args = server.command(tmp_path, "doc.adoc")
    assert args[:3] == ["asciidoctor-pdf", "--safe-mode", "secure"]
    assert server.EXTENSION in args and "pdf-theme=my-theme.yml" not in " ".join(args)


def test_build_rejects_bad_main_names():
    for main in ("", "x.txt", "../a.adoc"):
        with pytest.raises(server.BuildError, match="X-Main-File"):
            server.build(_zip({"a.adoc": b""}), main)


@pytest.fixture
def builder(monkeypatch):
    """The real HTTP handler, with the asciidoctor run replaced."""

    def fake_build(data, main):
        names = zipfile.ZipFile(io.BytesIO(data)).namelist()
        if main == "fail.adoc":
            raise server.BuildError(
                server.HTTPStatus.UNPROCESSABLE_ENTITY, "asciidoctor: ERROR: boom"
            )
        return b"%PDF " + json.dumps(sorted(names)).encode(), ["asciidoctor: WARNING: w"]

    monkeypatch.setattr(server, "build", fake_build)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def test_remote_compiler_round_trip(builder, tmp_path):
    (tmp_path / "doc.adoc").write_text("= Doc")
    (tmp_path / "logo.png").write_bytes(b"png")
    (tmp_path / "old.pdf").write_bytes(b"skip me")
    (tmp_path / "link.png").symlink_to(tmp_path / "logo.png")
    pdf, messages = RemotePdfCompiler(builder, 10).compile(str(tmp_path / "doc.adoc"))
    assert Path(pdf).read_bytes() == b'%PDF ["doc.adoc", "logo.png"]'
    assert messages == ["asciidoctor: WARNING: w"]


def test_remote_compiler_reports_failures(builder, tmp_path):
    (tmp_path / "fail.adoc").write_text("= Doc")
    with pytest.raises(ValueError, match="boom"):
        RemotePdfCompiler(builder, 10).compile(str(tmp_path / "fail.adoc"))
    with pytest.raises(ValueError, match="not reachable"):
        RemotePdfCompiler("http://127.0.0.1:9", 2).compile(str(tmp_path / "fail.adoc"))
