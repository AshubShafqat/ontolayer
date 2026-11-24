"""Regenerate synthetic, redistributable demo fixtures (no external data)."""

import csv
import hashlib
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1] / "examples"


def prop(
    kind: str = "string", description: str = "Business attribute", **extra: Any
) -> dict[str, Any]:
    return {"type": kind, "description": description, "required": True, **extra}


def write_example(
    name: str,
    types: dict[str, Any],
    links: dict[str, Any],
    tables: dict[str, tuple[list[str], list[list[Any]]]],
    mappings: dict[str, Any],
    metrics: dict[str, Any],
) -> None:
    root = ROOT / name
    root.mkdir(parents=True, exist_ok=True)
    for table, (headers, rows) in tables.items():
        with (root / f"{table}.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(headers)
            writer.writerows(rows)
    properties = {key: list(value["properties"]) for key, value in types.items()}
    policy = {"types": list(types), "metrics": list(metrics), "properties": properties}
    document = {
        "namespace": name,
        "version": "1.0.0",
        "description": f"Synthetic {name} demonstration",
        "types": types,
        "links": links,
        "mappings": mappings,
        "metrics": metrics,
        "policies": [
            {"role": "admin", "allow_pii": True, **policy},
            {"role": "analyst", **policy},
            {"role": "regional", "row_attributes": {"region": "region"}, **policy},
        ],
    }
    (root / "ontology.yaml").write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    actors = {
        "admin": {"id": "demo-admin", "roles": ["admin", "operator"]},
        "analyst": {"id": "demo-analyst", "roles": ["analyst"]},
        "north": {"id": "demo-north", "roles": ["regional"], "attributes": {"region": "north"}},
        "south": {"id": "demo-south", "roles": ["regional"], "attributes": {"region": "south"}},
        "guest": {"id": "demo-guest", "roles": []},
    }
    credentials = []
    for actor_name, actor in actors.items():
        actor["namespace"] = name
        (root / f"{actor_name}.yaml").write_text(yaml.safe_dump(actor), encoding="utf-8")
        credentials.append(
            {
                "token_sha256": hashlib.sha256(f"demo-{actor_name}-token".encode()).hexdigest(),
                "actor": actor,
            }
        )
    (root / "credentials.yaml").write_text(
        yaml.safe_dump({"credentials": credentials}), encoding="utf-8"
    )


def main() -> None:
    common = {"region": prop(description="Sales or operating region")}
    types = {
        "Customer": {"properties": {"name": prop(), "email": prop(pii=True), **common}},
        "Order": {"properties": {"date": prop("date"), "status": prop(), **common}},
        "Product": {"properties": {"name": prop(), "category": prop(), **common}},
        "OrderLine": {
            "properties": {
                "quantity": prop("integer"),
                "unit_price": prop("number", unit="USD"),
                "date": prop("date"),
                "status": prop(),
                **common,
            }
        },
    }
    for name, definition in types.items():
        definition.update(description=f"Business {name}", owner="retail-team", status="certified")
    links = {
        "placedBy": {
            "source": "Order",
            "target": "Customer",
            "description": "Purchasing customer",
            "cardinality": "one",
        },
        "partOf": {
            "source": "OrderLine",
            "target": "Order",
            "description": "Containing order",
            "cardinality": "one",
        },
        "forProduct": {
            "source": "OrderLine",
            "target": "Product",
            "description": "Purchased product",
            "cardinality": "one",
        },
    }
    tables = {
        "customers": (
            ["id", "name", "email", "region"],
            [
                ["C1", "North Customer", "north@example.invalid", "north"],
                ["C2", "South Customer", "south@example.invalid", "south"],
            ],
        ),
        "products": (
            ["id", "name", "category", "region"],
            [
                ["P1", "North Widget", "hardware", "north"],
                ["P2", "South Widget", "hardware", "south"],
            ],
        ),
        "orders": (
            ["id", "customer_id", "date", "status", "region"],
            [
                ["O1", "C1", "2026-10-05", "completed", "north"],
                ["O2", "C2", "2026-10-10", "completed", "south"],
                ["O3", "C1", "2026-10-15", "canceled", "north"],
                ["O4", "C1", "2026-11-02", "completed", "north"],
            ],
        ),
        "lines": (
            ["id", "order_id", "product_id", "quantity", "unit_price", "date", "status", "region"],
            [
                ["L1", "O1", "P1", 2, 100, "2026-10-05", "completed", "north"],
                ["L2", "O1", "P1", 1, 50, "2026-10-05", "completed", "north"],
                ["L3", "O2", "P2", 3, 100, "2026-10-10", "completed", "south"],
                ["L4", "O2", "P2", 1, 50, "2026-10-10", "completed", "south"],
                ["L5", "O3", "P1", 1, 999, "2026-10-15", "canceled", "north"],
                ["L6", "O4", "P1", 1, 80, "2026-11-02", "completed", "north"],
            ],
        ),
    }
    mappings = {}
    for table, type_name in [
        ("customers", "Customer"),
        ("orders", "Order"),
        ("products", "Product"),
        ("lines", "OrderLine"),
    ]:
        mappings[table] = {
            "type": type_name,
            "kind": "csv",
            "path": f"{table}.csv",
            "id_column": "id",
            "columns": {p: p for p in types[type_name]["properties"]},
        }
    mappings["orders"]["links"] = {"placedBy": "customer_id"}
    mappings["lines"]["links"] = {"partOf": "order_id", "forProduct": "product_id"}
    metric_common = {
        "owner": "finance",
        "filters": {"status": "completed"},
        "dimensions": ["region"],
        "date_field": "date",
        "status": "certified",
    }
    metrics = {
        "revenue": {
            **metric_common,
            "description": (
                "Completed line sales, excluding tax and shipping; "
                "no refunds or discounts in fixture"
            ),
            "type": "OrderLine",
            "aggregation": "sum_product",
            "fields": ["quantity", "unit_price"],
            "unit": "USD",
            "grain": "order line",
            "synonyms": ["sales"],
        },
        "order_count": {
            **metric_common,
            "description": "Number of completed orders",
            "type": "Order",
            "aggregation": "count",
            "unit": "orders",
            "grain": "order",
            "synonyms": ["orders", "order count"],
        },
        "items_sold": {
            **metric_common,
            "description": "Units on completed order lines",
            "type": "OrderLine",
            "aggregation": "sum",
            "fields": ["quantity"],
            "unit": "units",
            "grain": "order line",
            "synonyms": ["units sold"],
        },
    }
    write_example("retail", types, links, tables, mappings, metrics)
    agriculture_types = {
        "Harvest": {
            "description": "A crop harvest batch",
            "owner": "farm-team",
            "status": "certified",
            "properties": {
                "crop": prop(),
                "weight": prop("number", unit="kg"),
                "date": prop("date"),
                **common,
            },
        }
    }
    write_example(
        "agriculture",
        agriculture_types,
        {},
        {
            "harvests": (
                ["id", "crop", "weight", "date", "region"],
                [
                    ["H1", "wheat", 1200, "2026-10-01", "north"],
                    ["H2", "rice", 800, "2026-10-02", "south"],
                ],
            )
        },
        {
            "harvests": {
                "type": "Harvest",
                "kind": "csv",
                "path": "harvests.csv",
                "id_column": "id",
                "columns": {p: p for p in agriculture_types["Harvest"]["properties"]},
            }
        },
        {
            "harvest_weight": {
                "description": "Total harvested weight",
                "owner": "farm-team",
                "type": "Harvest",
                "aggregation": "sum",
                "fields": ["weight"],
                "dimensions": ["region", "crop"],
                "date_field": "date",
                "unit": "kg",
                "grain": "harvest batch",
                "status": "certified",
                "synonyms": ["harvest"],
            }
        },
    )


if __name__ == "__main__":
    main()
