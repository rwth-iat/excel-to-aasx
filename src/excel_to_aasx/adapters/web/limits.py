"""Cap request bodies before anything parses them.

Starlette spools uploaded files to disk with no size limit while parsing the form, before a
handler can check the size; a single large request could fill the disk.
"""

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BodyLimit:
    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self._app = app
        self._max = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        declared = dict(scope.get("headers") or []).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > self._max:
            await _reject(send, self._max)
            return
        seen, overflow = 0, False

        async def limited() -> Message:
            nonlocal seen, overflow
            message = await receive()
            seen += len(message.get("body", b""))
            if seen > self._max:
                overflow = True
                return {"type": "http.disconnect"}
            return message

        async def guarded(message: Message) -> None:
            # FastAPI answers a broken body with 400; the real answer is 413.
            if not overflow:
                await send(message)

        try:
            await self._app(scope, limited, guarded)
        except Exception:
            if not overflow:
                raise
        if overflow:
            await _reject(send, self._max)


async def _reject(send: Send, limit: int) -> None:
    body = f'{{"detail":"request larger than {limit} bytes"}}'.encode()
    await send({"type": "http.response.start", "status": 413,
                "headers": [(b"content-type", b"application/json"),
                            (b"content-length", str(len(body)).encode())]})  # fmt: skip
    await send({"type": "http.response.body", "body": body})
