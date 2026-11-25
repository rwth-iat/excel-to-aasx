"""PlantUML rendering for the live preview (ADR 0011)."""

import subprocess

import pytest

from excel_to_aasx.adapters.pdf import diagram
from excel_to_aasx.adapters.pdf.diagram import JAVA_ARGS, MAX_SVG_BYTES, DockerDiagramRenderer
from excel_to_aasx.app.render_diagram import render_diagram
from tests.adapters.test_pdf_compiler import IMAGE, needs_docker

DOCUMENT = "@startuml\nclass A\n@enduml\n"


def _run_returning(stdout: bytes, calls: list | None = None):
    def run(command, **kwargs):
        if calls is not None:
            calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout, b"")

    return run


def test_jvm_is_capped_and_sandboxed_on_the_command_line():
    for option in ("-Xmx256m", "-XX:ActiveProcessorCount=1", "-DPLANTUML_SECURITY_PROFILE=SANDBOX"):
        assert option in JAVA_ARGS


def test_container_is_locked_down(monkeypatch):
    calls: list = []
    monkeypatch.setattr(diagram.subprocess, "run", _run_returning(b"<?plantuml 1?><svg/>", calls))
    assert DockerDiagramRenderer(IMAGE, 5).render_svg(DOCUMENT) == b"<svg/>"
    command, kwargs = calls[0]
    joined = " ".join(command)
    for option in ("--network none", "--cap-drop ALL", "--read-only", "--cpus 1", "--ulimit cpu=10:10", "nice -n 10"):
        assert option in joined
    assert "-v" not in command  # no host folder is mounted
    assert kwargs["input"] == DOCUMENT.encode()


def test_no_svg_too_large_and_timeout_are_errors(monkeypatch):
    monkeypatch.setattr(diagram.subprocess, "run", _run_returning(b""))
    with pytest.raises(ValueError, match="could not be rendered"):
        DockerDiagramRenderer(IMAGE, 5).render_svg(DOCUMENT)
    monkeypatch.setattr(diagram.subprocess, "run", _run_returning(b"<svg" + b"x" * MAX_SVG_BYTES))
    with pytest.raises(ValueError, match="too large"):
        DockerDiagramRenderer(IMAGE, 5).render_svg(DOCUMENT)

    def slow(command, **kwargs):
        if command[1] == "run":
            raise subprocess.TimeoutExpired(command, 5)
        return subprocess.CompletedProcess(command, 0, b"", b"")

    monkeypatch.setattr(diagram.subprocess, "run", slow)
    with pytest.raises(ValueError, match="longer than 5 s"):
        DockerDiagramRenderer(IMAGE, 5).render_svg(DOCUMENT)


def test_use_case_checks_the_text_before_any_renderer_runs():
    seen: list[str] = []

    class Renderer:
        def render_svg(self, document: str) -> bytes:
            seen.append(document)
            return b"<svg/>"

    assert render_diagram(Renderer(), "class A") == b"<svg/>"
    with pytest.raises(ValueError, match="one @startuml"):
        render_diagram(Renderer(), "@startditaa\n+--+\n@endditaa")
    assert seen == [DOCUMENT]


@needs_docker
def test_renders_svg_and_blocks_includes():
    renderer = DockerDiagramRenderer(IMAGE, 120)
    svg = render_diagram(renderer, 'class "General" <<SMC>> {\n  +Name : xs:string\n}')
    assert svg.startswith(b"<svg") and b"General" in svg
    blocked = render_diagram(renderer, "!include /etc/passwd\nclass A")
    assert b"root:" not in blocked and b"cannot include" in blocked
