"""PDF builder service (ADR 0009): AsciiDoc folder as ZIP in, PDF out.

Runs inside the asciidoctor/docker-asciidoctor image on an internal network without internet
access. Standard library only (Python 3.12 in that image). Every request is untrusted: the
document comes from an anonymous web user.

POST /build     body: ZIP of a flat folder; header X-Main-File: the .adoc to build
POST /diagram   body: PlantUML text (UTF-8); returns SVG (ADR 0011)
GET  /health
"""

import io
import json
import os
import re
import resource
import signal
import subprocess
import sys
import tempfile
import threading
import zipfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MAX_ZIP_BYTES = int(os.environ.get("BUILDER_MAX_ZIP_BYTES", 60 * 1024 * 1024))
MAX_UNPACKED_BYTES = int(os.environ.get("BUILDER_MAX_UNPACKED_BYTES", 200 * 1024 * 1024))
MAX_FILES = 200
TIMEOUT_SECONDS = int(os.environ.get("BUILDER_TIMEOUT_SECONDS", 240))
EXTENSION = os.environ.get("BUILDER_EXTENSION", "/opt/builder/numbered_paragraphs.rb")
THEME = "my-theme.yml"
NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*")
BUILDS = threading.BoundedSemaphore(int(os.environ.get("BUILDER_PARALLEL", 2)))
# The jar asciidoctor-diagram ships in the image. Same JVM arguments as
# src/excel_to_aasx/adapters/pdf/diagram.py (a test keeps them equal): one core, small heap,
# the sandbox on the command line (not only in the image ENV), a bounded image size.
PLANTUML_JAR = os.environ.get(
    "BUILDER_PLANTUML_JAR",
    "/usr/lib/ruby/gems/3.4.0/gems/asciidoctor-diagram-plantuml-1.2026.2"
    "/lib/asciidoctor-diagram/plantuml/plantuml-lgpl-1.2026.2.jar",
)
JAVA_ARGS = [
    "java", "-Xmx256m", "-Xss1m", "-XX:ActiveProcessorCount=1", "-XX:+UseSerialGC",
    "-Djava.awt.headless=true",
    "-DPLANTUML_SECURITY_PROFILE=SANDBOX", "-DPLANTUML_LIMIT_SIZE=8192",
    "-jar", PLANTUML_JAR, "-tsvg", "-pipe",
]  # fmt: skip
MAX_DIAGRAM_BYTES = 64 * 1024
MAX_SVG_BYTES = 5 * 1024 * 1024
DIAGRAM_TIMEOUT_SECONDS = 15
CPU_SECONDS = 10  # below the wall-clock timeout, so a busy render is cut off first
MARKER = re.compile(rb"^\s*@(start|end)\w*", re.MULTILINE)
NEWPAGE = re.compile(rb"^\s*newpage\b", re.MULTILINE)
DIAGRAMS = threading.BoundedSemaphore(int(os.environ.get("BUILDER_PARALLEL_DIAGRAMS", 2)))


class BuildError(Exception):
    def __init__(self, status: HTTPStatus, message: str) -> None:
        super().__init__(message)
        self.status = status


def unpack(data: bytes, target: Path) -> None:
    """Flat folder only: plain names, no paths, bounded count and size. Never extractall."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as error:
        raise BuildError(HTTPStatus.BAD_REQUEST, "body is not a ZIP archive") from error
    members = archive.infolist()
    if len(members) > MAX_FILES:
        raise BuildError(HTTPStatus.BAD_REQUEST, f"more than {MAX_FILES} files")
    if sum(m.file_size for m in members) > MAX_UNPACKED_BYTES:
        raise BuildError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "archive unpacks too large")
    for member in members:
        if member.is_dir() or not NAME.fullmatch(member.filename):
            raise BuildError(HTTPStatus.BAD_REQUEST, f"invalid file name: {member.filename!r}")
        (target / member.filename).write_bytes(archive.read(member))


def command(folder: Path, main: str) -> list[str]:
    args = [
        "asciidoctor-pdf", "--safe-mode", "secure",
        "-r", "asciidoctor-diagram", "-r", EXTENSION,
        "-a", "toc=macro", "-a", "env-pdf",
    ]  # fmt: skip
    if (folder / THEME).is_file():
        args += ["-a", f"pdf-theme={THEME}"]
    return [*args, "-o", "out.pdf", main]


def _relocate_theme(folder: Path) -> None:
    """Package Explorer themes name fonts as /documents/<file> (its Docker mount point)."""
    theme = folder / THEME
    if theme.is_file():
        text = theme.read_text(encoding="utf-8", errors="replace")
        theme.write_text(text.replace("/documents/", f"{folder}/"), encoding="utf-8")


def build(data: bytes, main: str) -> tuple[bytes, list[str]]:
    if not NAME.fullmatch(main) or not main.endswith(".adoc"):
        raise BuildError(HTTPStatus.BAD_REQUEST, "X-Main-File must name an .adoc file")
    with tempfile.TemporaryDirectory(prefix="build-") as tmp:
        folder = Path(tmp)
        unpack(data, folder)
        if not (folder / main).is_file():
            raise BuildError(HTTPStatus.BAD_REQUEST, f"{main} is not in the archive")
        _relocate_theme(folder)
        process = subprocess.Popen(  # noqa: S603 - argument list, no shell
            command(folder, main), cwd=folder, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, start_new_session=True,
        )  # fmt: skip
        try:
            output, _ = process.communicate(timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as error:
            os.killpg(process.pid, signal.SIGKILL)  # Java (PlantUML) children too
            process.communicate()
            raise BuildError(
                HTTPStatus.GATEWAY_TIMEOUT, f"build timed out after {TIMEOUT_SECONDS}s"
            ) from error
        pdf = folder / "out.pdf"
        if process.returncode != 0 or not pdf.is_file():
            raise BuildError(HTTPStatus.UNPROCESSABLE_ENTITY, output[-4000:] or "build failed")
        messages = [line for line in output.splitlines() if line.startswith("asciidoctor:")]
        return pdf.read_bytes(), messages


def diagram_command() -> list[str]:
    """Limits are set in a fresh interpreter just before exec: preexec_fn is unsafe in threads."""
    limits = [str(CPU_SECONDS), str(MAX_SVG_BYTES)]
    return [sys.executable, os.path.abspath(__file__), "--exec-limited", *limits, *JAVA_ARGS]


def exec_limited(argv: list[str]) -> None:
    """CPU seconds (SIGXCPU), file size (SIGXFSZ, the SVG is written to a file), low priority."""
    cpu_seconds, max_bytes, command = int(argv[0]), int(argv[1]), argv[2:]
    # Soft limit sends SIGXCPU; the hard one, a second later, SIGKILL for anything that ignores it.
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
    resource.setrlimit(resource.RLIMIT_FSIZE, (max_bytes, max_bytes))
    os.nice(10)
    os.execvp(command[0], command)  # noqa: S606 - fixed argument list from diagram_command


def check_single_uml(source: bytes) -> None:
    """The app checks this too (domain/diagram_source.py); -pipe renders every pair."""
    markers = [m.group(0).strip() for m in MARKER.finditer(source)]
    if (
        len(markers) != 2
        or not markers[0].startswith(b"@startuml")
        or markers[1] != b"@enduml"
        or NEWPAGE.search(source)
    ):
        raise BuildError(HTTPStatus.BAD_REQUEST, "expected one @startuml ... @enduml diagram")


def render_diagram(source: bytes) -> bytes:
    """PlantUML draws syntax errors into the SVG, so a non-zero exit with an SVG is a result."""
    check_single_uml(source)
    with tempfile.TemporaryDirectory(prefix="diagram-") as tmp:
        svg_file = Path(tmp) / "out.svg"
        with svg_file.open("wb") as out:
            process = subprocess.Popen(  # noqa: S603 - argument list, no shell
                diagram_command(), cwd=tmp, stdin=subprocess.PIPE, stdout=out,
                stderr=subprocess.DEVNULL, start_new_session=True,
            )  # fmt: skip
            try:
                process.communicate(source, timeout=DIAGRAM_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired as error:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
                raise BuildError(
                    HTTPStatus.GATEWAY_TIMEOUT,
                    f"diagram took longer than {DIAGRAM_TIMEOUT_SECONDS}s",
                ) from error
        output = svg_file.read_bytes()
    if process.returncode == -signal.SIGXFSZ or len(output) >= MAX_SVG_BYTES:
        raise BuildError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "diagram SVG too large")
    if process.returncode in (-signal.SIGXCPU, -signal.SIGKILL):
        raise BuildError(HTTPStatus.UNPROCESSABLE_ENTITY, "diagram used too much CPU time")
    start = output.find(b"<svg")
    if start < 0:
        raise BuildError(HTTPStatus.UNPROCESSABLE_ENTITY, "PlantUML produced no SVG")
    return output[start:]


class Handler(BaseHTTPRequestHandler):
    server_version = "pdf-builder"
    sys_version = ""

    def do_GET(self) -> None:  # noqa: N802 - http.server naming
        if self.path == "/health":
            self._reply(HTTPStatus.OK, b"ok", "text/plain")
        else:
            self._reply(HTTPStatus.NOT_FOUND, b"not found", "text/plain")

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/diagram":
            self._diagram()
            return
        if self.path != "/build":
            self._reply(HTTPStatus.NOT_FOUND, b"not found", "text/plain")
            return
        length = self.headers.get("Content-Length", "")
        if not length.isdigit() or int(length) > MAX_ZIP_BYTES:
            self._reply(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE, b"missing or too large body", "text/plain"
            )
            return
        data = self.rfile.read(int(length))
        if not BUILDS.acquire(blocking=False):
            self._reply(HTTPStatus.TOO_MANY_REQUESTS, b"builder busy", "text/plain")
            return
        try:
            pdf, messages = build(data, self.headers.get("X-Main-File", ""))
        except BuildError as error:
            self._reply(error.status, str(error).encode("utf-8", "replace"), "text/plain")
            return
        finally:
            BUILDS.release()
        self._reply(
            HTTPStatus.OK, pdf, "application/pdf", {"X-Build-Messages": json.dumps(messages)[:4000]}
        )

    def _diagram(self) -> None:
        length = self.headers.get("Content-Length", "")
        if not length.isdigit() or int(length) > MAX_DIAGRAM_BYTES:
            self._reply(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE, b"missing or too large body", "text/plain"
            )
            return
        source = self.rfile.read(int(length))
        if not DIAGRAMS.acquire(blocking=False):
            self._reply(HTTPStatus.TOO_MANY_REQUESTS, b"builder busy", "text/plain")
            return
        try:
            svg = render_diagram(source)
        except BuildError as error:
            self._reply(error.status, str(error).encode("utf-8", "replace"), "text/plain")
            return
        finally:
            DIAGRAMS.release()
        self._reply(HTTPStatus.OK, svg, "image/svg+xml")

    def _reply(
        self, status: HTTPStatus, body: bytes, content_type: str, extra: dict | None = None
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        # Status lines only; never document content.
        print(f"{self.address_string()} {format % args}", flush=True)


def main() -> None:
    port = int(os.environ.get("BUILDER_PORT", 8080))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()  # noqa: S104 - internal network only


if __name__ == "__main__":
    if sys.argv[1:2] == ["--exec-limited"]:
        exec_limited(sys.argv[2:])
    main()
