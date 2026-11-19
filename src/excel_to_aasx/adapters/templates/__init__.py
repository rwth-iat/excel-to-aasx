"""Starter document templates shipped with the package (ADR 0008)."""

import re
from pathlib import Path

from excel_to_aasx.domain.document.starter import Frame

ROOT = Path(__file__).parent


def load_frame(name: str = "idta") -> Frame:
    folder = ROOT / name
    if not re.fullmatch(r"[a-z0-9-]+", name) or not folder.is_dir():
        raise ValueError(f"unknown document template '{name}'")
    parts: dict[str, list[str]] = {}
    current = None
    for line in (folder / "frame.adoc").read_text(encoding="utf-8").splitlines():
        if found := re.fullmatch(r"//@part (\w+)", line):
            current = parts.setdefault(found.group(1), [])
        elif current is not None:
            current.append(line)
    assets = {p.name: p.read_bytes() for p in sorted((folder / "assets").iterdir()) if p.is_file()}
    return Frame({k: "\n".join(v).strip("\n") for k, v in parts.items()}, assets)
