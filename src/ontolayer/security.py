"""Bounded ASGI requests, security headers and single-process abuse limits."""

import time
from collections import deque
from threading import Lock
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class SecurityMiddleware:
    def __init__(self, app: ASGIApp, max_body: int = 65536, requests_per_minute: int = 240):
        self.app = app
        self.max_body = max_body
        self.requests_per_minute = requests_per_minute
        self.windows: dict[str, deque[float]] = {}
        self.lock = Lock()

    def allowed(self, client: str) -> bool:
        now = time.monotonic()
        with self.lock:
            if len(self.windows) >= 10000:
                self.windows = {k: v for k, v in self.windows.items() if v[-1] > now - 60}
                if client not in self.windows and len(self.windows) >= 10000:
                    return False
            window = self.windows.setdefault(client, deque())
            while window and window[0] <= now - 60:
                window.popleft()
            if len(window) >= self.requests_per_minute:
                return False
            window.append(now)
            return True

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id

        async def secure_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
                headers["X-Content-Type-Options"] = "nosniff"
                headers["X-Frame-Options"] = "DENY"
                headers["Referrer-Policy"] = "no-referrer"
                headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
                headers["Cache-Control"] = "no-store"
                # Swagger has its own external assets; the product UI has no external dependencies.
                if scope["path"] not in {"/docs", "/redoc"}:
                    headers["Content-Security-Policy"] = (
                        "default-src 'self'; script-src 'self'; style-src 'self'; "
                        "img-src 'self' data:; connect-src 'self'; "
                        "object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
                    )
            await send(message)

        async def reject(status: int, detail: str) -> None:
            response = JSONResponse(
                {
                    "detail": detail,
                    "request_id": request_id,
                    "code": f"http_{status}",
                    "message": detail,
                    "hint": "Reduce request size or wait before retrying.",
                },
                status_code=status,
            )
            if status == 429:
                response.headers["Retry-After"] = "60"
            await response(scope, receive, secure_send)

        if scope["path"].startswith("/v1/"):
            client = str(scope.get("client", ("unknown",))[0])
            if not self.allowed(client):
                await reject(429, "Request limit reached. Please retry in a minute.")
                return
        headers = Headers(scope=scope)
        try:
            if int(headers.get("content-length", "0")) > self.max_body:
                await reject(413, "Request body exceeds 64 KiB")
                return
        except ValueError:
            await reject(400, "Invalid content length")
            return
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > self.max_body:
                await reject(413, "Request body exceeds 64 KiB")
                return
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, secure_send)
