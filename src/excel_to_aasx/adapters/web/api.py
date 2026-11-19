"""Request handlers. One method per endpoint; routes are declared in create_app."""

import json
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from excel_to_aasx.adapters.web.files import read_limited, safe_child, zip_folder
from excel_to_aasx.adapters.web.workspaces import WorkspaceFull, Workspaces
from excel_to_aasx.domain.document.opened import OpenedDocument

UPLOAD_TYPES = (".xlsx", ".aasx")
AASX_TYPE = "application/asset-administration-shell-package"


@dataclass(frozen=True)
class WebServices:
    open_upload: Callable[[str, str], OpenedDocument]
    compile_pdf: Callable[[str], tuple[str, list[str]]]


@dataclass(frozen=True)
class WebLimits:
    max_upload_bytes: int = 50 * 1024 * 1024
    max_document_bytes: int = 2 * 1024 * 1024
    parallel_builds: int = 2


class Api:
    def __init__(self, services: WebServices, workspaces: Workspaces, limits: WebLimits) -> None:
        self._services = services
        self._workspaces = workspaces
        self._limits = limits
        self._builds = threading.BoundedSemaphore(limits.parallel_builds)

    async def upload(self, file: UploadFile) -> JSONResponse:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in UPLOAD_TYPES:
            raise HTTPException(400, "upload an .xlsx workbook or an .aasx package")
        data = await read_limited(file, self._limits.max_upload_bytes)
        try:
            workspace_id, folder = self._workspaces.create()
        except WorkspaceFull as error:
            raise HTTPException(503, "too many open sessions, try again later") from error
        source = folder / f"upload{suffix}"
        source.write_bytes(data)
        try:
            opened = await run_in_threadpool(self._services.open_upload, str(source), str(folder))
        except ValueError as error:
            self._workspaces.delete(workspace_id)
            raise HTTPException(400, str(error)) from error
        main = Path(opened.main_file)
        record = {"package": Path(opened.package).name, "main": main.name}
        (folder / "meta.json").write_text(json.dumps(record), encoding="utf-8")
        return JSONResponse({
            "id": workspace_id,
            "kind": suffix[1:],
            "issues": [vars(issue) for issue in opened.issues],
            "document": {"name": main.name, "text": opened.document.text},
        })  # fmt: skip

    def package(self, workspace_id: str) -> FileResponse:
        folder = self._folder(workspace_id)
        path = folder / self._meta(folder)["package"]
        return FileResponse(path, filename="package.aasx", media_type=AASX_TYPE)

    def asset(self, workspace_id: str, name: str) -> FileResponse:
        path = safe_child(self._folder(workspace_id) / "doc", name)
        if path is None:
            raise HTTPException(404, "no such file")
        response = FileResponse(path)
        # Package files are untrusted: an SVG opened directly must not run scripts.
        response.headers["Content-Security-Policy"] = "sandbox; default-src 'none'"
        return response

    async def save(self, workspace_id: str, request: Request) -> Response:
        self._write_document(self._folder(workspace_id), await self._text(request))
        return Response(status_code=204)

    def download_zip(self, workspace_id: str) -> Response:
        data = zip_folder(self._folder(workspace_id) / "doc", skip_suffixes=(".pdf",))
        disposition = {"Content-Disposition": 'attachment; filename="document.zip"'}
        return Response(data, media_type="application/zip", headers=disposition)

    async def pdf(self, workspace_id: str, request: Request) -> FileResponse:
        main = self._write_document(self._folder(workspace_id), await self._text(request))
        if not self._builds.acquire(blocking=False):
            raise HTTPException(429, "the PDF builder is busy, try again in a few seconds")
        try:
            path, messages = await run_in_threadpool(self._services.compile_pdf, str(main))
        except ValueError as error:
            raise HTTPException(422, f"PDF build failed: {error}") from error
        finally:
            self._builds.release()
        headers = {"X-Build-Messages": json.dumps(messages)[:2000]}
        return FileResponse(path, media_type="application/pdf", headers=headers)

    def close(self, workspace_id: str) -> Response:
        self._workspaces.delete(workspace_id)
        return Response(status_code=204)

    def _folder(self, workspace_id: str) -> Path:
        folder = self._workspaces.get(workspace_id)
        if folder is None:
            raise HTTPException(404, "session not found or expired")
        return folder

    def _meta(self, folder: Path) -> dict[str, str]:
        return json.loads((folder / "meta.json").read_text(encoding="utf-8"))

    def _write_document(self, folder: Path, text: str) -> Path:
        main = folder / "doc" / self._meta(folder)["main"]
        main.write_text(text, encoding="utf-8")
        return main

    async def _text(self, request: Request) -> str:
        limit, body = self._limits.max_document_bytes, b""
        async for chunk in request.stream():
            body += chunk
            if len(body) > limit:
                raise HTTPException(413, f"document larger than {limit} bytes")
        try:
            return body.decode("utf-8")
        except UnicodeDecodeError as error:
            raise HTTPException(400, "document must be UTF-8 text") from error
