"""Trusted, local CSV and read-only SQLite source adapters."""

import csv
import hashlib
import sqlite3
from datetime import date
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

from ontolayer.backend import GraphBackend
from ontolayer.models import Edge, Entity, Ontology, Scalar, SourceMapping


def read_rows(mapping: SourceMapping, root: Path) -> tuple[list[dict[str, Any]], str]:
    path = (root / mapping.path).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Source path must remain inside the ontology directory")
    snapshot = hashlib.sha256(path.read_bytes()).hexdigest()
    if mapping.kind == "csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle)), snapshot
    table = str(mapping.table).replace('"', '""')
    connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    try:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(f'SELECT * FROM "{table}"').fetchall()
        return [dict(row) for row in rows], snapshot
    finally:
        connection.close()


def convert(value: Any, kind: str) -> Scalar:
    if kind == "integer":
        return int(str(value))
    if kind == "number":
        result = Decimal(str(value))
        if not result.is_finite():
            raise ValueError("Non-finite numbers are not supported")
        if len(result.as_tuple().digits) > 28:
            raise ValueError("Numeric values must have at most 28 significant digits")
        if not -28 <= int(result.as_tuple().exponent) <= 28:
            raise ValueError("Numeric exponents must be between -28 and 28")
        if result.as_tuple().exponent == 0:
            with localcontext() as context:
                context.prec = 80
                result = result.quantize(Decimal("0.0"))
        return result
    if kind == "boolean":
        normalized = str(value).lower()
        if normalized not in {"true", "false", "1", "0"}:
            raise ValueError("Invalid boolean")
        return normalized in {"true", "1"}
    if kind == "date":
        return date.fromisoformat(str(value)).isoformat()
    return str(value)


def ingest(ontology: Ontology, root: Path, backend: GraphBackend) -> dict[str, int]:
    entities: list[Entity] = []
    edges: list[Edge] = []
    seen: set[str] = set()
    for mapping_name, mapping in ontology.mappings.items():
        rows, snapshot = read_rows(mapping, root)
        properties = ontology.types[mapping.type].properties
        for row in rows:
            raw_id = row.get(mapping.id_column)
            if raw_id is None or not str(raw_id).strip():
                raise ValueError("Source row has missing identifier")
            entity_id = f"{mapping.type}:{raw_id}"
            if entity_id in seen:
                raise ValueError("Duplicate source identifier")
            seen.add(entity_id)
            values = {
                name: convert(row[column], properties[name].type)
                for name, column in mapping.columns.items()
                if row.get(column) is not None and row[column] != ""
            }
            entities.append(
                Entity(
                    id=entity_id,
                    type=mapping.type,
                    properties=values,
                    source=mapping.path,
                    mapping=mapping_name,
                    snapshot=snapshot,
                )
            )
            for relation, column in mapping.links.items():
                target = row.get(column)
                if target is not None and str(target).strip():
                    edges.append(
                        Edge(
                            source=entity_id,
                            relation=relation,
                            target=f"{ontology.links[relation].target}:{target}",
                        )
                    )
    backend.upsert(entities, edges)
    return {"entities": len(entities), "edges": len(edges)}
