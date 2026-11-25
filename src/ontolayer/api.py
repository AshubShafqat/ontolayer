"""Authenticated REST transport over the same semantic service."""

import hashlib
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from prometheus_client import CollectorRegistry, Counter, generate_latest
from pydantic import Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from ontolayer import __version__
from ontolayer.auth import authenticate, load_credentials
from ontolayer.models import Actor, Model
from ontolayer.security import SecurityMiddleware
from ontolayer.service import Denied, Service
from ontolayer.web import answer, workspace


class ToolRequest(Model):
    arguments: dict[str, Any] = Field(default_factory=dict)


class QuestionRequest(Model):
    question: str = Field(min_length=1, max_length=2000)


def create_app(
    service: Service,
    credentials_file: Path,
    *,
    demo: bool = False,
    production: bool = False,
    allowed_hosts: list[str] | None = None,
    requests_per_minute: int = 240,
) -> FastAPI:
    credentials = load_credentials(credentials_file)
    if production:
        if demo:
            raise ValueError("Demo mode cannot be used in production")
        if not allowed_hosts or "*" in allowed_hosts:
            raise ValueError("Production requires explicit allowed hosts")
        if service.audit.path is None:
            raise ValueError("Production requires an audit log")
        demo_hashes = {
            hashlib.sha256(f"demo-{role}-token".encode()).hexdigest()
            for role in ("admin", "analyst", "north", "south", "guest")
        }
        if any(c.token_sha256 in demo_hashes for c in credentials.credentials):
            raise ValueError("Public demo credentials cannot be used in production")
    app = FastAPI(
        title="OntoLayer",
        version=__version__,
        description="Governed business semantic API",
        docs_url=None if production else "/docs",
        redoc_url=None,
        openapi_url=None if production else "/openapi.json",
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=allowed_hosts
        or [
            "localhost",
            "127.0.0.1",
            "[::1]",
            "testserver",
        ],
    )
    app.add_middleware(SecurityMiddleware, requests_per_minute=requests_per_minute)
    assets = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=assets), name="static")
    bearer = HTTPBearer(auto_error=False)
    registry = CollectorRegistry()
    calls = Counter("ontolayer_requests", "Semantic requests", ["outcome"], registry=registry)

    def identity(
        credential: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ) -> Actor:
        if credential is None:
            raise HTTPException(401, "Bearer token required")
        try:
            actor = authenticate(credential.credentials, credentials_file)
            if actor.namespace != service.ontology.namespace:
                raise HTTPException(403, "Not available to this caller")
            return actor
        except ValueError as error:
            raise HTTPException(401, "Invalid credential") from error

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(assets / "index.html")

    @app.get("/v1/config", tags=["Application"])
    def config() -> dict[str, Any]:
        return {"demo": demo, "version": __version__, "docs": not production}

    @app.get("/v1/workspace", tags=["Application"])
    def workspace_view(actor: Annotated[Actor, Depends(identity)]) -> dict[str, Any]:
        return workspace(service, actor)

    @app.post("/v1/ask", tags=["Application"])
    def ask_view(
        body: QuestionRequest, actor: Annotated[Actor, Depends(identity)]
    ) -> dict[str, Any]:
        try:
            result = answer(service, actor, body.question)
        except (ValueError, TypeError) as error:
            raise HTTPException(
                400, "Choose a permitted metric and valid filters or dates."
            ) from error
        return result

    @app.get("/health", tags=["Operations"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/tools/{operation}", tags=["Semantic tools"])
    def execute(
        operation: str,
        body: ToolRequest,
        actor: Annotated[Actor, Depends(identity)],
    ) -> dict[str, Any]:
        try:
            result = service.call(actor, operation, **body.arguments)
        except Denied as error:
            calls.labels("denied").inc()
            raise HTTPException(403, "Not available to this caller") from error
        except (ValueError, TypeError) as error:
            calls.labels("invalid").inc()
            raise HTTPException(400, "Invalid operation or arguments") from error
        calls.labels("allowed").inc()
        return result

    @app.get("/metrics")
    def metrics(actor: Annotated[Actor, Depends(identity)]) -> Response:
        if "operator" not in actor.roles:
            raise HTTPException(403, "Operator role required")
        return Response(generate_latest(registry), media_type="text/plain; version=0.0.4")

    return app
