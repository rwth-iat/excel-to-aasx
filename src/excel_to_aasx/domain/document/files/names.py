"""File names for document assets (ExportSmt.ProcessImageLink)."""

import re


def asset_name(id_short: str, extension: str) -> str:
    """`my-theme_dot_yml` -> `my-theme.yml`; otherwise idShort plus the guessed extension."""
    name = re.sub(r"[^a-zA-Z0-9_-]", "_", id_short)
    position = name.lower().rfind("_dot_")
    if position >= 0:
        extension = "." + name[position + len("_dot_") :]
        name = name[:position]
    return name + extension


def safe_file_name(name: str) -> str:
    """A name from untrusted args must stay inside the output folder."""
    base = name.replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]", "_", base).lstrip(".")
    return cleaned or "asset"
