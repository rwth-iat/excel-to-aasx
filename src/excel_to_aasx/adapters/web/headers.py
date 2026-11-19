"""Security headers for every response."""

from fastapi import FastAPI, Request

# The preview is an iframe with `srcdoc` and no scripts; it inherits this policy, so its
# images must come from 'self' and its styles from our stylesheet.
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; "
    "frame-src 'self' blob:; object-src 'none'; base-uri 'none'; form-action 'self'; "
    "frame-ancestors 'none'"
)


def csp_with_style_nonce(nonce: str) -> str:
    """CodeMirror injects <style> elements; it tags them with this nonce (EditorView.cspNonce)."""
    return CSP.replace("style-src 'self'", f"style-src 'self' 'nonce-{nonce}'")


def add_security_headers(app: FastAPI) -> None:
    @app.middleware("http")
    async def headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("Content-Security-Policy", CSP)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        return response
