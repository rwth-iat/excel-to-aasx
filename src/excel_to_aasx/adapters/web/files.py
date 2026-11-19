"""File helpers for the web adapter: bounded uploads, safe names, ZIP downloads."""

import io
import re
import zipfile
from pathlib import Path

from fastapi import HTTPException, UploadFile

_NAME = re.compile(r"[A-Za-z0-9_.-]+")


async def read_limited(file: UploadFile, limit: int) -> bytes:
    data = b""
    while chunk := await file.read(1024 * 1024):
        data += chunk
        if len(data) > limit:
            raise HTTPException(413, f"upload larger than {limit // (1024 * 1024)} MB")
    return data


def safe_child(folder: Path, name: str) -> Path | None:
    """A plain file name inside `folder`, or None. No paths, no hidden files."""
    if not _NAME.fullmatch(name) or name.startswith("."):
        return None
    path = folder / name
    # The PDF container writes into this folder too; never follow a link out of it.
    if path.is_symlink() or path.parent.resolve() != folder.resolve() or not path.is_file():
        return None
    return path


def zip_folder(folder: Path, skip_suffixes: tuple[str, ...] = ()) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(folder.iterdir()):
            if (
                path.is_file()
                and not path.is_symlink()
                and path.suffix.lower() not in skip_suffixes
            ):
                archive.write(path, path.name)
    return buffer.getvalue()
