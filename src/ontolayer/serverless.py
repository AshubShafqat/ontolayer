"""Production-profile, read-only student demo for ephemeral Python hosts."""

import base64
import tempfile
from pathlib import Path

from fastapi import FastAPI

from ontolayer.api import create_app
from ontolayer.service import AuditLog, Service


def create_serverless_app(environment: dict[str, str], root: Path) -> FastAPI:
    hosts = list(
        dict.fromkeys(
            value
            for key in ("VERCEL_URL", "VERCEL_PROJECT_PRODUCTION_URL", "ONTOLAYER_PUBLIC_HOST")
            if (value := environment.get(key))
        )
    )
    if not hosts or any(any(c.isspace() or c in "/*:" for c in host) for host in hosts):
        raise ValueError("Configure exact public hostnames for the serverless deployment")
    decoded = {}
    for key, filename in (
        ("ONTOLAYER_CREDENTIALS_B64", "credentials.yaml"),
        ("ONTOLAYER_PUBLIC_DEMO_B64", "public-demo.json"),
    ):
        value = environment.get(key, "")
        if not value:
            raise ValueError(f"Missing deployment setting: {key}")
        try:
            decoded[filename] = base64.b64decode(value, validate=True)
        except ValueError:
            raise ValueError(f"Invalid encoded deployment setting: {key}") from None
    state = Path(tempfile.mkdtemp(prefix="ontolayer-"))
    for filename, content in decoded.items():
        path = state / filename
        path.write_bytes(content)
        path.chmod(0o600)
    service = Service.from_file(
        root / "examples/retail/ontology.yaml", AuditLog(state / "audit.jsonl")
    )
    # A serverless replica cannot safely publish a shared mutable ontology snapshot.
    # Keep certification/editing on the full local or persistent-container deployment.
    return create_app(
        service,
        state / "credentials.yaml",
        production=True,
        allowed_hosts=hosts,
        public_demo_tokens=state / "public-demo.json",
    )
