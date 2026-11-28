import base64
import hashlib
import json
import secrets
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from ontolayer.auth import actor_from_file
from ontolayer.serverless import create_serverless_app
from tests.conftest import RETAIL


def test_serverless_production_roles_and_host_boundary() -> None:
    tokens = {role: secrets.token_urlsafe(32) for role in ("north", "south", "analyst")}
    credentials = yaml.safe_dump(
        {
            "credentials": [
                {
                    "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
                    "actor": actor_from_file(RETAIL / f"{role}.yaml").model_dump(),
                }
                for role, token in tokens.items()
            ]
        }
    )
    environment = {
        "VERCEL_URL": "testserver",
        "ONTOLAYER_CREDENTIALS_B64": base64.b64encode(credentials.encode()).decode(),
        "ONTOLAYER_PUBLIC_DEMO_B64": base64.b64encode(json.dumps(tokens).encode()).decode(),
    }
    client = TestClient(create_serverless_app(environment, Path.cwd()))
    assert client.get("/health").status_code == 200
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/docs").status_code == 404
    assert client.get("/health", headers={"Host": "untrusted.example"}).status_code == 400
    assert client.get("/v1/config").json()["public_demo_tokens"] == tokens
    for role, expected in (("north", 250), ("south", 350), ("analyst", 600)):
        response = client.post(
            "/v1/tools/query_metric",
            json={
                "arguments": {
                    "metric_id": "revenue",
                    "start_date": "2026-10-01",
                    "end_date": "2026-11-01",
                }
            },
            headers={"Authorization": f"Bearer {tokens[role]}"},
        )
        assert response.status_code == 200, response.text
        assert float(response.json()["values"]["total"]) == expected
    for invalid in ("*", "https://example.com", "bad\nhost"):
        with pytest.raises(ValueError, match="hostnames"):
            create_serverless_app({**environment, "VERCEL_URL": invalid}, Path.cwd())
    with pytest.raises(ValueError, match="Missing deployment"):
        create_serverless_app({"VERCEL_URL": "testserver"}, Path.cwd())
