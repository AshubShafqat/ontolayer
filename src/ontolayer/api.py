"""Authenticated REST transport over the same semantic service."""

from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from prometheus_client import CollectorRegistry, Counter, generate_latest
from pydantic import Field

from ontolayer.auth import authenticate
from ontolayer.models import Actor, Model
from ontolayer.service import Denied, Service


class ToolRequest(Model):
    arguments: dict[str, Any] = Field(default_factory=dict)


def create_app(service: Service, credentials_file: Path) -> FastAPI:
    app = FastAPI(title="OntoLayer", version="0.1.0", description="Governed business semantic API")
    bearer = HTTPBearer(auto_error=False)
    registry = CollectorRegistry()
    calls = Counter("ontolayer_requests", "Semantic requests", ["outcome"], registry=registry)

    def identity(
        credential: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ) -> Actor:
        if credential is None:
            raise HTTPException(401, "Bearer token required")
        try:
            return authenticate(credential.credentials, credentials_file)
        except ValueError as error:
            raise HTTPException(401, "Invalid credential") from error

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/tools/{operation}")
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
