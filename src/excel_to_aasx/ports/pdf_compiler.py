from typing import Protocol


class PdfCompiler(Protocol):
    def compile(self, adoc_file: str) -> tuple[str, list[str]]:
        """Build the PDF next to `adoc_file`. Returns its path and the tool's messages.

        Raises `ValueError` when the build fails.
        """
        ...
