"""Temporary per-session folders (ADR 0005): random ids, idle expiry, a cap on their number."""

import re
import secrets
import shutil
import threading
import time
from pathlib import Path

_ID = re.compile(r"[0-9a-f]{32}")


class WorkspaceFull(Exception):
    pass


class Workspaces:
    def __init__(self, root: Path, idle_seconds: int, max_count: int) -> None:
        self._root = root
        self._idle = idle_seconds
        self._max = max_count
        self._lock = threading.Lock()
        # Uploads are private: other local users must not read them.
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        root.chmod(0o700)

    def create(self) -> tuple[str, Path]:
        with self._lock:
            self.expire()
            if sum(1 for _ in self._root.iterdir()) >= self._max:
                raise WorkspaceFull
            workspace_id = secrets.token_hex(16)
            folder = self._root / workspace_id
            folder.mkdir(mode=0o700)
            return workspace_id, folder

    def get(self, workspace_id: str) -> Path | None:
        """The folder, or None for an unknown, malformed or expired id. Touches it."""
        if not _ID.fullmatch(workspace_id):
            return None
        folder = self._root / workspace_id
        if not folder.is_dir():
            return None
        if time.time() - folder.stat().st_mtime > self._idle:
            shutil.rmtree(folder, ignore_errors=True)
            return None
        folder.touch()
        return folder

    def delete(self, workspace_id: str) -> None:
        if (folder := self.get(workspace_id)) is not None:
            shutil.rmtree(folder, ignore_errors=True)

    def expire(self) -> None:
        now = time.time()
        for folder in self._root.iterdir():
            if folder.is_dir() and now - folder.stat().st_mtime > self._idle:
                shutil.rmtree(folder, ignore_errors=True)
