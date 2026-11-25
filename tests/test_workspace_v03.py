import json

import pytest
from fastapi.testclient import TestClient

from ontolayer.api import create_app
from ontolayer.service import Denied, Service
from ontolayer.workbench import Workbench
from tests.conftest import RETAIL


def test_diagnostics_are_authenticated_and_scoped(service):
    client = TestClient(create_app(service, RETAIL / "credentials.yaml"))
    north = {"Authorization": "Bearer demo-north-token"}
    guest = {"Authorization": "Bearer demo-guest-token"}
    for path in ("catalog", "audit", "validation"):
        assert client.get(f"/v1/{path}").status_code == 401
    assert len(client.get("/v1/catalog", headers=north).json()["tools"]) == 11
    client.post(
        "/v1/tools/get_lineage", headers=north, json={"arguments": {"entity_id": "Customer:C2"}}
    )
    events = client.get("/v1/audit", headers=north).json()["items"]
    assert any(e["outcome"] == "denied_or_invalid" for e in events)
    assert all(e["actor"] == "demo-north" for e in events)
    assert client.get("/v1/audit", headers=guest).json()["items"] == []
    assert client.get("/v1/validation", headers=guest).json()["findings"] == []


def test_certification_is_explicit_atomic_and_survives_restart(service, admin, north, tmp_path):
    manager = Workbench(service, tmp_path)
    snapshot = manager.document(admin)
    candidate = snapshot["document"]
    candidate["version"] = "1.0.1"
    candidate["types"]["Customer"]["description"] = "Reviewed customer definition"
    draft = manager.preview(admin, candidate, snapshot["revision"], {})
    assert service.ontology.version == "1.0.0"
    assert draft["entities"] > 0
    assert "Reviewed customer definition" in draft["diff"]
    with pytest.raises(Denied):
        manager.certify(north, draft["id"], snapshot["revision"])
    result = manager.certify(admin, draft["id"], snapshot["revision"])
    assert result["version"] == service.ontology.version == "1.0.1"
    assert service.ontology.types["Customer"].status == "certified"
    with pytest.raises(ValueError, match="Stale"):
        manager.certify(admin, draft["id"], snapshot["revision"])
    fresh = Service.from_file(RETAIL / "ontology.yaml")
    Workbench(fresh, tmp_path)
    assert fresh.ontology.version == "1.0.1"
    assert (
        fresh.call(north, "query_metric", metric_id="revenue")["values"]
        == service.call(north, "query_metric", metric_id="revenue")["values"]
    )
    assert "owl:Ontology" in manager.export(admin, "turtle")
    assert json.loads(manager.export(admin, "json"))["version"] == "1.0.1"
    assert "version: 1.0.1" in manager.export(admin, "yaml")
    with pytest.raises(ValueError):
        manager.export(admin, "html")


def test_csv_preview_cannot_write_active_data_until_certification(service, admin, tmp_path):
    manager = Workbench(service, tmp_path)
    snapshot = manager.document(admin)
    snapshot["document"]["version"] = "1.0.1"
    mapping = snapshot["document"]["mappings"]["customers"]
    csv_text = (RETAIL / mapping["path"]).read_text().replace("Alice", "Reviewed Alice")
    draft = manager.preview(
        admin, snapshot["document"], snapshot["revision"], {"customers": csv_text}
    )
    assert service.ontology.version == "1.0.0"
    manager.certify(admin, draft["id"], snapshot["revision"])
    assert service.ontology.version == "1.0.1"
    assert service.source_root.is_relative_to(tmp_path)


@pytest.mark.parametrize(
    "case", ["path", "namespace", "version", "stale", "headers", "large", "unknown", "bad_id"]
)
def test_workbench_rejects_unsafe_or_invalid_proposals(service, admin, tmp_path, case):
    manager = Workbench(service, tmp_path)
    snapshot = manager.document(admin)
    doc = snapshot["document"]
    doc["version"] = "1.0.1"
    uploads = {}
    if case == "path":
        doc["mappings"]["customers"]["path"] = "../../secret.csv"
    if case == "namespace":
        doc["namespace"] = "other"
    if case == "version":
        doc["version"] = "1.0.0"
    if case == "stale":
        snapshot["revision"] = "a" * 64
    if case == "headers":
        uploads["customers"] = "id,id\n1,1"
    if case == "large":
        uploads["customers"] = "a" * 48001
    if case == "unknown":
        uploads["unknown"] = "id\n1"
    with pytest.raises(ValueError):
        if case == "bad_id":
            manager.certify(admin, "../../secret", snapshot["revision"])
        else:
            manager.preview(admin, doc, snapshot["revision"], uploads)
    assert service.ontology.version == "1.0.0"
    assert not (tmp_path / "retail" / "active.json").exists()


def test_workbench_api_authorization_errors_and_commit(service, tmp_path):
    client = TestClient(
        create_app(service, RETAIL / "credentials.yaml", workspace_directory=tmp_path)
    )
    admin = {"Authorization": "Bearer demo-admin-token"}
    north = {"Authorization": "Bearer demo-north-token"}
    assert client.get("/v1/ontology", headers=north).status_code == 403
    snapshot = client.get("/v1/ontology", headers=admin).json()
    snapshot["document"]["version"] = "1.0.1"
    assert client.post("/v1/drafts/validate", headers=admin, json=snapshot).json()["valid"]
    assert not client.post(
        "/v1/drafts/validate",
        headers=admin,
        json={"document": "types: broken", "revision": snapshot["revision"]},
    ).json()["valid"]
    result = client.post("/v1/drafts/preview", headers=admin, json=snapshot)
    assert result.status_code == 200, result.text
    draft = result.json()
    assert (
        client.post(
            f"/v1/drafts/{draft['id']}/certify",
            headers=north,
            json={"revision": snapshot["revision"]},
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/v1/drafts/{draft['id']}/certify",
            headers=admin,
            json={"revision": snapshot["revision"]},
        ).status_code
        == 200
    )
    assert client.get("/v1/ontology/export?format=turtle", headers=admin).status_code == 200
    error = client.post("/v1/tools/query_metric", headers=admin, json={"extra": 1})
    assert error.status_code == 422
    assert error.json()["request_id"] == error.headers["X-Request-ID"]
    assert all(k in error.json() for k in ("code", "message", "hint"))
