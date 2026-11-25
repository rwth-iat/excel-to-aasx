"""Render PlantUML diagrams for the live preview (ADR 0011).

The text comes from an anonymous web user. PlantUML runs with the SANDBOX security profile
(no !include of files or URLs), set on the command line so no environment can drop it, with
a capped JVM, in the diagram service or in a locked-down container without network.
"""

import logging
import os
import subprocess
import urllib.error
import urllib.request
import uuid

from excel_to_aasx.domain.diagram_source import RendererBusy

# The jar asciidoctor-diagram ships in the pinned image (ADR 0004); it moves with the image.
PLANTUML_JAR = (
    "/usr/lib/ruby/gems/3.4.0/gems/asciidoctor-diagram-plantuml-1.2026.2"
    "/lib/asciidoctor-diagram/plantuml/plantuml-lgpl-1.2026.2.jar"
)
# One core, a small heap, the sandbox, a bounded image size. builder/server.py uses the same.
JAVA_ARGS = [
    "java", "-Xmx256m", "-Xss1m", "-XX:ActiveProcessorCount=1", "-XX:+UseSerialGC",
    "-Djava.awt.headless=true",
    "-DPLANTUML_SECURITY_PROFILE=SANDBOX", "-DPLANTUML_LIMIT_SIZE=8192",
    "-jar", PLANTUML_JAR, "-tsvg", "-pipe",
]  # fmt: skip
CPU_SECONDS = 10
MAX_SVG_BYTES = 5 * 1024 * 1024
FAILED = "the diagram could not be rendered"
log = logging.getLogger(__name__)


def _svg(output: bytes) -> bytes:
    if len(output) > MAX_SVG_BYTES:
        raise ValueError(f"the diagram is too large (over {MAX_SVG_BYTES // 2**20} MB of SVG)")
    start = output.find(b"<svg")
    if start < 0:
        raise ValueError(FAILED)
    return output[start:]


class DockerDiagramRenderer:
    def __init__(self, image: str, timeout_seconds: int) -> None:
        self._image = image
        self._timeout = timeout_seconds

    def render_svg(self, document: str) -> bytes:
        name = f"excel-to-aasx-uml-{uuid.uuid4().hex[:12]}"
        command = [
            "docker", "run", "--rm", "-i", "--name", name,
            "--network", "none",
            "--user", f"{os.getuid()}:{os.getgid()}",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--read-only", "--tmpfs", "/tmp:rw,size=64m",  # noqa: S108 - inside the container
            "--memory", "512m", "--pids-limit", "128", "--cpus", "1",
            "--ulimit", f"cpu={CPU_SECONDS}:{CPU_SECONDS}",
            "-e", "HOME=/tmp", "-w", "/tmp",
            self._image, "nice", "-n", "10", *JAVA_ARGS,
        ]  # fmt: skip
        try:
            result = subprocess.run(  # noqa: S603 - argument list, no shell
                command,
                input=document.encode("utf-8"),
                capture_output=True,
                timeout=self._timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            subprocess.run(["docker", "kill", name], capture_output=True, check=False)  # noqa: S603, S607
            raise ValueError(f"the diagram took longer than {self._timeout} s") from error
        except FileNotFoundError as error:
            raise ValueError("docker is not installed or not on PATH") from error
        if b"<svg" not in result.stdout:
            log.warning("diagram container failed: %s", result.stderr[-2000:])
        return _svg(result.stdout)


class RemoteDiagramRenderer:
    def __init__(self, base_url: str, timeout_seconds: int) -> None:
        self._url = base_url.rstrip("/") + "/diagram"
        self._timeout = timeout_seconds

    def render_svg(self, document: str) -> bytes:
        request = urllib.request.Request(  # noqa: S310 - URL comes from our own configuration
            self._url,
            data=document.encode("utf-8"),
            headers={"Content-Type": "text/plain; charset=utf-8"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:  # noqa: S310
                return _svg(response.read(MAX_SVG_BYTES + 1))
        except urllib.error.HTTPError as error:
            detail = error.read(2000).decode("utf-8", "replace")
            log.warning("diagram service answered %s: %s", error.code, detail)
            if error.code == 429:
                raise RendererBusy("the diagram renderer is busy") from error
            raise ValueError(FAILED) from error
        except (urllib.error.URLError, TimeoutError) as error:
            log.warning("diagram service not reachable: %s", error)
            raise ValueError("the diagram renderer is not available") from error
