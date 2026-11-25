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
from excel_to_aasx.adapters.web.throttle import SessionThrottle
from excel_to_aasx.adapters.web.workspaces import WorkspaceFull, Workspaces
from excel_to_aasx.domain.diagram_source import RendererBusy
from excel_to_aasx.domain.document.opened import OpenedDocument

UPLOAD_TYPES = (".xlsx", ".aasx")
AASX_TYPE = "application/asset-administration-shell-package"


@dataclass(frozen=True)
class WebServices:
    open_upload: Callable[[str, str], OpenedDocument]
    compile_pdf: Callable[[str], tuple[str, list[str]]]
    render_diagram: Callable[[str], bytes]


@dataclass(frozen=True)
class WebLimits:
    max_upload_bytes: int = 50 * 1024 * 1024
    max_document_bytes: int = 2 * 1024 * 1024
    parallel_builds: int = 2
    parallel_uploads: int = 4
    max_diagram_bytes: int = 64 * 1024
    parallel_diagrams: int = 2
    diagram_gap_seconds: float = 2.0
    diagram_budget_seconds: float = 60.0  # render time per session per 10 minutes
    max_error_chars: int = 4000


class Api:
    def __init__(self, services: WebServices, workspaces: Workspaces, limits: WebLimits) -> None:
        self._services = services
        self._workspaces = workspaces
        self._limits = limits
        self._builds = threading.BoundedSemaphore(limits.parallel_builds)
        self._uploads = threading.BoundedSemaphore(limits.parallel_uploads)
        self._diagrams = threading.BoundedSemaphore(limits.parallel_diagrams)
        self._throttle = SessionThrottle(limits.diagram_gap_seconds, limits.diagram_budget_seconds)

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
        if not self._uploads.acquire(blocking=False):
            self._workspaces.delete(workspace_id)
            raise HTTPException(429, "the server is busy, try again in a few seconds")
        try:
            opened = await run_in_threadpool(self._services.open_upload, str(source), str(folder))
        except ValueError as error:
            self._workspaces.delete(workspace_id)
            raise HTTPException(400, self._short(str(error))) from error
        finally:
            self._uploads.release()
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
            raise HTTPException(422, self._short(f"PDF build failed: {error}")) from error
        finally:
            self._builds.release()
        headers = {"X-Build-Messages": json.dumps(messages)[:2000]}
        return FileResponse(path, media_type="application/pdf", headers=headers)

    async def diagram(self, workspace_id: str, request: Request) -> Response:
        self._folder(workspace_id)
        source = await self._text(request, self._limits.max_diagram_bytes)
        if refused := self._throttle.start(workspace_id):
            raise HTTPException(429, refused)
        try:
            svg = await self._render(source)
        finally:
            self._throttle.finish(workspace_id)
        # Untrusted SVG: shown through <img>, and sandboxed if opened directly.
        headers = {"Content-Security-Policy": "sandbox; default-src 'none'; style-src 'unsafe-inline'"}
        return Response(svg, media_type="image/svg+xml", headers=headers)

    async def _render(self, source: str) -> bytes:
        if not self._diagrams.acquire(blocking=False):
            raise HTTPException(429, "the diagram renderer is busy, try again in a few seconds")
        try:
            return await run_in_threadpool(self._services.render_diagram, source)
        except RendererBusy as error:
            raise HTTPException(429, str(error)) from error
        except ValueError as error:
            raise HTTPException(422, self._short(f"diagram failed: {error}")) from error
        finally:
            self._diagrams.release()

    def close(self, workspace_id: str) -> Response:
        self._workspaces.delete(workspace_id)
        self._throttle.forget(workspace_id)
        return Response(status_code=204)

    def _short(self, message: str) -> str:
        """Tool output can be long; keep its end, where the cause usually is."""
        limit = self._limits.max_error_chars
        return message if len(message) <= limit else "…" + message[-limit:]

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

    async def _text(self, request: Request, limit: int | None = None) -> str:
        limit, body = limit or self._limits.max_document_bytes, b""
        async for chunk in request.stream():
            body += chunk
            if len(body) > limit:
                raise HTTPException(413, f"text larger than {limit} bytes")
        try:
            return body.decode("utf-8")
        except UnicodeDecodeError as error:
            raise HTTPException(400, "document must be UTF-8 text") from error
