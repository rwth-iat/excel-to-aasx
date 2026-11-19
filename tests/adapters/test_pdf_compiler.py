import shutil
import subprocess
from pathlib import Path

import pytest

from excel_to_aasx.adapters import pdf as pdf_module
from excel_to_aasx.adapters.pdf import DockerPdfCompiler

IMAGE = "asciidoctor/docker-asciidoctor:1.108.1"


class _Recorder:
    def __init__(self, returncode=0, stdout="", stderr="", raises=None, make_pdf=True):
        self.calls: list[list[str]] = []
        self._result = subprocess.CompletedProcess([], returncode, stdout, stderr)
        self._raises = raises
        self._make_pdf = make_pdf

    def __call__(self, command, **kwargs):
        self.calls.append(command)
        if self._raises and command[1] == "run":
            raise self._raises
        if self._make_pdf and command[1] == "run":
            Path(command[-1]).with_suffix(".pdf").write_bytes(b"%PDF")
        return self._result


@pytest.fixture
def adoc(tmp_path, monkeypatch):
    (tmp_path / "doc.adoc").write_text("= Doc\n")
    monkeypatch.chdir(tmp_path)
    return tmp_path / "doc.adoc"


def _compile(monkeypatch, adoc, recorder):
    monkeypatch.setattr(pdf_module.subprocess, "run", recorder)
    return DockerPdfCompiler(IMAGE, 5).compile(str(adoc))


def test_container_is_locked_down_and_secure_mode(monkeypatch, adoc):
    recorder = _Recorder(stderr="asciidoctor: WARNING: x\nnoise")
    path, messages = _compile(monkeypatch, adoc, recorder)
    command = " ".join(recorder.calls[0])
    flags = [
        "--network none", "--cap-drop ALL", "--read-only", "--security-opt no-new-privileges",
        "--pids-limit", "--memory", "--safe-mode secure", f"{IMAGE} asciidoctor-pdf",
    ]  # fmt: skip
    for flag in flags:
        assert flag in command
    assert "/extensions/numbered_paragraphs.rb" in command
    assert "extended.rb" not in command
    assert "pdf-theme" not in command  # no theme file in the folder
    assert path.endswith("doc.pdf") and messages == ["asciidoctor: WARNING: x"]


def test_theme_is_used_when_present(monkeypatch, adoc):
    (adoc.parent / "my-theme.yml").write_text("extends: default\n")
    recorder = _Recorder()
    _compile(monkeypatch, adoc, recorder)
    assert "pdf-theme=my-theme.yml" in recorder.calls[0]


def test_failure_reports_output(monkeypatch, adoc):
    with pytest.raises(ValueError, match="exit 1"):
        _compile(monkeypatch, adoc, _Recorder(returncode=1, stderr="boom", make_pdf=False))


def test_timeout_kills_container(monkeypatch, adoc):
    recorder = _Recorder(raises=subprocess.TimeoutExpired("docker", 5))
    with pytest.raises(ValueError, match="timed out"):
        _compile(monkeypatch, adoc, recorder)
    assert recorder.calls[1][:2] == ["docker", "kill"]


def test_missing_docker(monkeypatch, adoc):
    with pytest.raises(ValueError, match="docker is not installed"):
        _compile(monkeypatch, adoc, _Recorder(raises=FileNotFoundError()))


def _image_available() -> bool:
    if shutil.which("docker") is None:
        return False
    found = subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True, check=False)
    return found.returncode == 0


needs_docker = pytest.mark.skipif(
    not _image_available(), reason=f"docker image {IMAGE} not present"
)


@needs_docker
@pytest.mark.skipif(shutil.which("pdftotext") is None, reason="pdftotext not installed")
def test_secure_mode_blocks_reading_host_files(tmp_path):
    adoc = tmp_path / "evil.adoc"
    adoc.write_text("= Evil\n\nbefore\n\ninclude::/etc/passwd[]\n\nafter\n")
    path, _ = DockerPdfCompiler(IMAGE, 120).compile(str(adoc))
    text = subprocess.run(
        ["pdftotext", path, "-"], capture_output=True, text=True, check=True
    ).stdout
    assert "before" in text and "after" in text
    assert "root:" not in text
