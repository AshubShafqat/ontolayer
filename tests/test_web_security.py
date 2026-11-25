import hashlib
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from ontolayer.api import create_app
from ontolayer.auth import load_credentials
from ontolayer.service import AuditLog, Service
from tests.conftest import RETAIL


def client(service: Service, **kwargs) -> TestClient:
    return TestClient(create_app(service, RETAIL / "credentials.yaml", **kwargs))


HEADERS = {"Authorization": "Bearer demo-north-token"}


def test_web_assets_and_security_headers(service: Service) -> None:
    app = client(service)
    response = app.get("/")
    assert response.status_code == 200
    assert "Business knowledge workspace" in response.text
    assert "script-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-frame-options"] == "DENY"
    assert len(response.headers["x-request-id"]) == 32
    assert app.get("/static/app.js").status_code == 200
    assert app.get("/static/app.css").status_code == 200
    assert app.get("/v1/config").json()["demo"] is False
    assert client(service, demo=True).get("/v1/config").json()["demo"] is True
    assert app.get("/", headers={"Host": "attacker.invalid"}).status_code == 400


def test_workspace_is_policy_scoped(service: Service) -> None:
    app = client(service)
    assert app.get("/v1/workspace").status_code == 401
    result = app.get("/v1/workspace", headers=HEADERS).json()
    assert result["actor"]["attributes"] == {"region": "north"}
    customer = next(c for c in result["concepts"] if c["id"] == "Customer")
    assert "email" not in customer["properties"]
    guest = app.get("/v1/workspace", headers={"Authorization": "Bearer demo-guest-token"}).json()
    assert guest["concepts"] == guest["metrics"] == guest["links"] == []


def test_web_questions_compute_and_clarify(service: Service) -> None:
    app = client(service)
    response = app.post(
        "/v1/ask", headers=HEADERS, json={"question": "revenue from 2026-10-01 to 2026-11-01"}
    )
    assert response.json()["result"]["values"] == {"total": "250.0"}
    assert response.json()["answerable"]
    unclear = app.post("/v1/ask", headers=HEADERS, json={"question": "profit next year"})
    assert unclear.json()["answerable"] is False
    assert (
        app.post("/v1/ask", headers=HEADERS, json={"question": "revenue by email"}).status_code
        == 400
    )
    assert app.post("/v1/ask", headers=HEADERS, json={"question": ""}).status_code == 422
    assert app.post("/v1/ask", headers=HEADERS, json={"question": "x" * 2001}).status_code == 422


@pytest.mark.parametrize(
    "arguments",
    [
        {"metric_id": ["revenue"]},
        {"metric_id": "revenue", "filters": "region=north"},
        {"metric_id": "revenue", "filters": {"region": ["north"]}},
        {"metric_id": "revenue", "group_by": 123},
        {"metric_id": "revenue", "extra": "x"},
    ],
)
def test_invalid_tool_arguments_are_client_errors(service: Service, arguments: dict) -> None:
    response = client(service).post(
        "/v1/tools/query_metric", headers=HEADERS, json={"arguments": arguments}
    )
    assert response.status_code == 400
    assert "traceback" not in response.text.lower()


def test_rate_and_body_limits(service: Service) -> None:
    app = client(service, requests_per_minute=2)
    assert app.get("/v1/config").status_code == 200
    assert app.get("/v1/config").status_code == 200
    limited = app.get("/v1/config")
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "60"
    app = client(service)
    assert app.post("/v1/ask", content=b"x" * 65537).status_code == 413
    assert app.post("/v1/ask", content=iter([b"x" * 40000, b"y" * 40000])).status_code == 413


def test_production_startup_guards(service: Service, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Demo mode"):
        client(service, demo=True, production=True)
    with pytest.raises(ValueError, match="allowed hosts"):
        client(service, production=True)
    with pytest.raises(ValueError, match="audit log"):
        client(service, production=True, allowed_hosts=["workspace.example"])
    service.audit = AuditLog(tmp_path / "audit.jsonl")
    with pytest.raises(ValueError, match="demo credentials"):
        client(service, production=True, allowed_hosts=["workspace.example"])


def test_production_app_private_credentials(service: Service, tmp_path: Path) -> None:
    service.audit = AuditLog(tmp_path / "audit.jsonl")
    config = load_credentials(RETAIL / "credentials.yaml").model_dump()
    config["credentials"] = [config["credentials"][0]]
    config["credentials"][0]["token_sha256"] = hashlib.sha256(
        b"private-test-only-token"
    ).hexdigest()
    path = tmp_path / "credentials.yaml"
    path.write_text(yaml.safe_dump(config))
    app = TestClient(create_app(service, path, production=True, allowed_hosts=["testserver"]))
    assert app.get("/docs").status_code == 404
    assert app.get("/openapi.json").status_code == 404
    assert not app.get("/v1/config").json()["demo"]
    headers = {"Authorization": "Bearer private-test-only-token"}
    assert app.get("/v1/workspace", headers=headers).status_code == 200
    config["credentials"][0]["actor"]["namespace"] = "different-tenant"
    path.write_text(yaml.safe_dump(config))
    assert app.get("/v1/workspace", headers=headers).status_code == 403


def test_duplicate_credentials_fail(service: Service, tmp_path: Path) -> None:
    config = load_credentials(RETAIL / "credentials.yaml").model_dump()
    config["credentials"].append(config["credentials"][0])
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match="unique"):
        create_app(service, path)
