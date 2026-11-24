import json
from pathlib import Path

import pytest

from ontolayer.auth import actor_from_file
from ontolayer.models import Actor
from ontolayer.service import AuditLog, Denied, Service
from tests.conftest import RETAIL, ROOT


@pytest.mark.parametrize(
    "actor_name, expected", [("admin", "600.0"), ("north", "250.0"), ("south", "350.0")]
)
def test_authorization_before_aggregation(service: Service, actor_name: str, expected: str) -> None:
    actor = actor_from_file(RETAIL / f"{actor_name}.yaml")
    result = service.call(
        actor, "query_metric", metric_id="revenue", start_date="2026-10-01", end_date="2026-11-01"
    )
    assert result["values"] == {"total": expected}
    assert result["status"] == "certified"
    assert result["ontology_version"] == "1.0.0"
    assert result["lineage"][0]["mapping"] == "lines"
    assert len(result["lineage"][0]["snapshot_sha256"]) == 64


def test_grouping_and_filters(service: Service, admin: Actor, north: Actor) -> None:
    assert service.call(admin, "query_metric", metric_id="revenue", group_by="region")[
        "values"
    ] == {"north": "330.0", "south": "350.0"}
    assert service.call(north, "query_metric", metric_id="revenue", filters={"region": "south"})[
        "values"
    ] == {"total": "0"}
    assert service.call(admin, "query_metric", metric_id="order_count")["values"] == {"total": "3"}
    assert service.call(admin, "query_metric", metric_id="items_sold")["values"] == {"total": "8"}


def test_basic_iso_dates_are_normalized(service: Service, north: Actor) -> None:
    result = service.call(
        north, "query_metric", metric_id="revenue", start_date="20261001", end_date="20261101"
    )
    assert result["values"] == {"total": "250.0"}
    assert result["start_date"] == "2026-10-01"


def test_rows_pii_and_metadata_filtered(service: Service, admin: Actor, north: Actor) -> None:
    customer = service.call(north, "list_entities", concept="Customer")["items"]
    assert len(customer) == 1
    assert customer[0]["id"] == "Customer:C1"
    assert "email" not in customer[0]["properties"]
    assert "email" not in service.call(north, "get_concept", concept="Customer")["properties"]
    assert "email" in service.call(admin, "get_concept", concept="Customer")["properties"]
    for entity_id in ("Customer:C2", "Customer:does-not-exist"):
        with pytest.raises(Denied, match="Not available"):
            service.call(north, "get_lineage", entity_id=entity_id)
        assert service.call(north, "explain_policy_decision", entity_id=entity_id) == {
            "allowed": False,
            "reason": "Not available to this caller",
        }
    assert service.call(north, "get_lineage", entity_id="Customer:C1")["mapping"] == "customers"


def test_paths_cannot_bridge_hidden_nodes(service: Service, north: Actor) -> None:
    path = service.call(north, "find_path", source="Customer:C1", target="Product:P1")
    assert path["nodes"][0] == "Customer:C1"
    assert path["nodes"][-1] == "Product:P1"
    assert (
        service.call(north, "find_path", source="Customer:C1", target="Product:P1", max_depth=1)[
            "nodes"
        ]
        == []
    )
    with pytest.raises(Denied):
        service.call(north, "find_path", source="Customer:C1", target="Product:P2")
    links = service.call(north, "get_relationships", entity_id="Order:O1")["items"]
    assert len(links) == 3
    assert all("C2" not in json.dumps(link) for link in links)


def test_default_deny_and_tenant_isolation(service: Service, north: Actor) -> None:
    guest = Actor(id="unknown", namespace="retail")
    assert service.call(guest, "search_terms")["items"] == []
    assert not service.call(guest, "check_answerable", metric_id="revenue")["answerable"]
    for operation, args in [
        ("list_entities", {"concept": "Customer"}),
        ("query_metric", {"metric_id": "revenue"}),
        ("list_ontology_versions", {}),
    ]:
        with pytest.raises(Denied):
            service.call(guest, operation, **args)
    with pytest.raises(Denied):
        service.call(north.model_copy(update={"namespace": "another-tenant"}), "search_terms")
    no_attribute = north.model_copy(update={"attributes": {}})
    assert service.call(no_attribute, "list_entities", concept="Order")["items"] == []


def test_pagination_search_and_versions(service: Service, admin: Actor) -> None:
    first = service.call(admin, "list_entities", concept="OrderLine", limit=2)
    assert first["next_offset"] == 2
    second = service.call(admin, "list_entities", concept="OrderLine", offset=2, limit=2)
    assert first["items"][0]["id"] != second["items"][0]["id"]
    assert service.call(admin, "search_terms", query="sales")["items"][0]["id"] == "revenue"
    assert service.call(admin, "list_ontology_versions")["versions"] == ["1.0.0"]


@pytest.mark.parametrize(
    "args",
    [
        {"group_by": "email"},
        {"filters": {"status": "canceled"}},
        {"filters": {"region": {"$ne": "south"}}},
        {"start_date": "bad"},
        {"start_date": "2026-11-01", "end_date": "2026-10-01"},
    ],
)
def test_invalid_metric_queries(service: Service, admin: Actor, args: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        service.call(admin, "query_metric", metric_id="revenue", **args)


def test_drafts_are_not_executable(service: Service, admin: Actor) -> None:
    service.ontology.metrics["revenue"].status = "draft"
    assert not service.call(admin, "check_answerable", metric_id="revenue")["answerable"]
    with pytest.raises(ValueError, match="draft"):
        service.call(admin, "query_metric", metric_id="revenue")


def test_audit_has_outcomes_not_sensitive_values(
    service: Service, north: Actor, tmp_path: Path
) -> None:
    path = tmp_path / "audit.jsonl"
    service.audit = AuditLog(path)
    service.call(north, "query_metric", metric_id="revenue")
    with pytest.raises(Denied):
        service.call(north, "get_lineage", entity_id="Customer:C2")
    events = [json.loads(line) for line in path.read_text().splitlines()]
    assert [e["outcome"] for e in events] == ["allowed", "denied_or_invalid"]
    assert "Customer:C2" not in path.read_text()


def test_agriculture_is_not_retail_specific() -> None:
    root = ROOT / "examples" / "agriculture"
    service = Service.from_file(root / "ontology.yaml")
    actor = actor_from_file(root / "north.yaml")
    assert service.call(actor, "query_metric", metric_id="harvest_weight")["values"] == {
        "total": "1200.0"
    }


def test_unsupported_calls_and_bounds(service: Service, admin: Actor) -> None:
    for operation, args in [
        ("raw_sql", {}),
        ("search_terms", {"limit": 1000}),
        ("find_path", {"source": "x", "target": "y", "max_depth": 20}),
    ]:
        with pytest.raises(ValueError):
            service.call(admin, operation, **args)
