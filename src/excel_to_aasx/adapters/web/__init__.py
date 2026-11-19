"""The web app (ADR 0005-0007): upload, download, edit with HTML preview, PDF on request.

Use-cases arrive as callables from main.py. Everything a visitor sends is untrusted.
"""

import secrets
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from excel_to_aasx.adapters.web.api import Api, WebLimits, WebServices
from excel_to_aasx.adapters.web.headers import add_security_headers, csp_with_style_nonce
from excel_to_aasx.adapters.web.workspaces import Workspaces

__all__ = ["WebLimits", "WebServices", "Workspaces", "create_app"]

STATIC = Path(__file__).parent / "static"


def create_app(services: WebServices, workspaces: Workspaces, limits: WebLimits) -> FastAPI:
    app = FastAPI(title="excel-to-aasx", docs_url=None, redoc_url=None, openapi_url=None)
    add_security_headers(app)
    api = Api(services, workspaces, limits)
    base = "/api/workspaces"
    app.add_api_route("/", _index, methods=["GET"])
    app.add_api_route(base, api.upload, methods=["POST"])
    app.add_api_route(base + "/{workspace_id}", api.close, methods=["DELETE"])
    app.add_api_route(base + "/{workspace_id}/package.aasx", api.package, methods=["GET"])
    app.add_api_route(base + "/{workspace_id}/files/{name}", api.asset, methods=["GET"])
    app.add_api_route(base + "/{workspace_id}/document", api.save, methods=["PUT"])
    app.add_api_route(base + "/{workspace_id}/document.zip", api.download_zip, methods=["GET"])
    app.add_api_route(base + "/{workspace_id}/pdf", api.pdf, methods=["POST"])
    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app


def _index() -> HTMLResponse:
    nonce = secrets.token_urlsafe(16)
    html = (STATIC / "index.html").read_text(encoding="utf-8").replace("{{nonce}}", nonce)
    return HTMLResponse(html, headers={"Content-Security-Policy": csp_with_style_nonce(nonce)})
