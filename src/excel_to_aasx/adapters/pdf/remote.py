"""Send PDF builds to the builder service (ADR 0009) instead of starting containers."""

import io
import json
import urllib.error
import urllib.request
import zipfile
from pathlib import Path


class RemotePdfCompiler:
    def __init__(self, base_url: str, timeout_seconds: int) -> None:
        self._url = base_url.rstrip("/") + "/build"
        self._timeout = timeout_seconds

    def compile(self, adoc_file: str) -> tuple[str, list[str]]:
        """Returns the PDF path and asciidoctor's messages. Raises `ValueError` on failure."""
        source = Path(adoc_file)
        request = urllib.request.Request(  # noqa: S310 - URL comes from our own configuration
            self._url,
            data=_zip_folder(source.parent),
            headers={"Content-Type": "application/zip", "X-Main-File": source.name},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:  # noqa: S310
                pdf = response.read()
                messages = json.loads(response.headers.get("X-Build-Messages") or "[]")
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", "replace")
            raise ValueError(f"PDF build failed ({error.code}):\n{detail}") from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise ValueError(f"PDF builder not reachable: {error}") from error
        target = source.with_suffix(".pdf")
        target.write_bytes(pdf)
        return str(target), [str(m) for m in messages]


def _zip_folder(folder: Path) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(folder.iterdir()):
            if path.is_file() and not path.is_symlink() and path.suffix.lower() != ".pdf":
                archive.write(path, path.name)
    return buffer.getvalue()
