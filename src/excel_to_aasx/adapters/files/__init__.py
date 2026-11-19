"""Write a rendered document and its assets into a folder."""

from pathlib import Path

from excel_to_aasx.domain.document.render import RenderedDocument


class FolderDocumentWriter:
    def write(self, target: str, document: RenderedDocument) -> str:
        """Returns the path of the written .adoc file."""
        folder = Path(target)
        folder.mkdir(parents=True, exist_ok=True)
        root = folder.resolve()
        for name, data in document.assets.items():
            _inside(root, name).write_bytes(data)
        main = _inside(root, document.file_name)
        main.write_text(document.text, encoding="utf-8")
        return str(main)


def _inside(root: Path, name: str) -> Path:
    path = (root / name).resolve()
    if path.parent != root:
        raise ValueError(f"refusing to write '{name}' outside {root}")
    return path
