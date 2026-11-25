"""Compile AsciiDoc to PDF with asciidoctor-pdf in a locked-down Docker container.

The document folder comes from an uploaded package, so the container gets no network, no
capabilities, a read-only root, resource limits and a timeout. Asciidoctor runs in secure
mode. Only our own extensions are loaded, never Ruby files from the package.
"""

import os
import subprocess
import uuid
from pathlib import Path

EXTENSIONS = Path(__file__).parent / "extensions"
THEME = "my-theme.yml"


class DockerPdfCompiler:
    def __init__(self, image: str, timeout_seconds: int, memory: str = "1g") -> None:
        self._image = image
        self._timeout = timeout_seconds
        self._memory = memory

    def compile(self, adoc_file: str) -> tuple[str, list[str]]:
        """Returns the PDF path and asciidoctor's messages. Raises `ValueError` on failure."""
        source = Path(adoc_file).resolve()
        target = source.with_suffix(".pdf")
        name = f"excel-to-aasx-pdf-{uuid.uuid4().hex[:12]}"
        command = [*self._docker_args(name, source.parent), *self._asciidoctor_args(source)]
        try:
            result = subprocess.run(  # noqa: S603 - argument list, no shell
                command, capture_output=True, text=True, timeout=self._timeout, check=False
            )
        except subprocess.TimeoutExpired as error:
            kill = ["docker", "kill", name]
            subprocess.run(kill, capture_output=True, check=False)  # noqa: S603, S607
            raise ValueError(f"PDF build timed out after {self._timeout}s") from error
        except FileNotFoundError as error:
            raise ValueError("docker is not installed or not on PATH") from error
        output = (result.stdout + result.stderr).strip()
        if result.returncode != 0 or not target.is_file():
            raise ValueError(f"PDF build failed (exit {result.returncode}):\n{output}")
        return str(target), [
            line for line in output.splitlines() if line.startswith("asciidoctor:")
        ]

    def _docker_args(self, name: str, folder: Path) -> list[str]:
        return [
            "docker", "run", "--rm", "--name", name,
            "--network", "none",
            "--user", f"{os.getuid()}:{os.getgid()}",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--read-only", "--tmpfs", "/tmp:rw,size=256m",  # noqa: S108 - inside the container
            "--memory", self._memory, "--pids-limit", "256", "--cpus", "2",
            "-e", "HOME=/tmp", "-e", "PLANTUML_SECURITY_PROFILE=SANDBOX",
            "-v", f"{folder}:/documents:rw",
            "-v", f"{EXTENSIONS}:/extensions:ro",
            "-w", "/documents",
            self._image,
        ]  # fmt: skip

    def _asciidoctor_args(self, source: Path) -> list[str]:
        args = [
            "asciidoctor-pdf", "--safe-mode", "secure",
            "-r", "asciidoctor-diagram",
            "-r", "/extensions/numbered_paragraphs.rb",
            "-a", "toc=macro", "-a", "env-pdf",
        ]  # fmt: skip
        if (source.parent / THEME).is_file():
            args += ["-a", f"pdf-theme={THEME}"]
        return [*args, "-o", source.with_suffix(".pdf").name, source.name]
