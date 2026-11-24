import csv
import json
import sqlite3
from pathlib import Path

import pytest
from jsonschema import validate
from pydantic import ValidationError
from rdflib import Graph

from ontolayer.backend import MemoryBackend
from ontolayer.models import Edge, Entity, Ontology, SourceMapping
from ontolayer.proposals import certify, draft_csv, propose
from ontolayer.sources import convert, ingest, read_rows
from ontolayer.spec import export_graph, lint, load, write_schema
from tests.conftest import RETAIL


def test_schema_export_and_no_drift(tmp_path: Path) -> None:
    ontology = load(RETAIL / "ontology.yaml")
    output = tmp_path / "schema.json"
    write_schema(output)
    schema = json.loads(output.read_text())
    validate(ontology.model_dump(), schema)
    committed = RETAIL.parents[1] / "spec" / "ontology.schema.json"
    assert json.loads(committed.read_text()) == schema
    graph = export_graph(ontology)
    assert len(Graph().parse(data=graph.serialize(format="turtle"), format="turtle")) == len(graph)
    assert lint(ontology) == []


@pytest.mark.parametrize(
    "mutator",
    [
        lambda o: o["links"]["partOf"].update(target="Missing"),
        lambda o: o["metrics"]["revenue"].update(fields=["quantity"]),
        lambda o: o["metrics"]["revenue"].update(fields=["status", "quantity"]),
        lambda o: o["mappings"]["lines"]["columns"].update(no_such_property="x"),
        lambda o: o["types"]["Customer"].update(interfaces=["Missing"]),
        lambda o: o["policies"][0].update(metrics=["Missing"]),
    ],
)
def test_bad_references_rejected(mutator) -> None:
    data = load(RETAIL / "ontology.yaml").model_dump()
    mutator(data)
    with pytest.raises(ValidationError):
        Ontology.model_validate(data)


def test_idempotence_and_atomic_failure() -> None:
    ontology = load(RETAIL / "ontology.yaml")
    backend = MemoryBackend()
    backend.apply_schema(ontology)
    counts = ingest(ontology, RETAIL, backend)
    ingest(ontology, RETAIL, backend)
    assert len(backend.entities()) == counts["entities"] == 14
    original = backend.export()
    bad = Entity(
        id="Customer:bad",
        type="Customer",
        properties={"region": "north"},
        source="x",
        mapping="x",
        snapshot="x",
    )
    with pytest.raises(ValueError, match="SHACL"):
        backend.upsert([bad], [])
    assert len(backend.entities()) == 14
    assert len(Graph().parse(data=original, format="turtle")) == len(backend.graph)
    with pytest.raises(ValueError, match="Dangling"):
        backend.upsert(
            [], [Edge(source="Order:O1", relation="placedBy", target="Customer:missing")]
        )
    with pytest.raises(ValueError, match="migrate"):
        backend.apply_schema(ontology)


def test_sqlite_adapter_and_path_boundary(tmp_path: Path) -> None:
    path = tmp_path / "data.sqlite"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE customer (id TEXT, name TEXT)")
    connection.execute("INSERT INTO customer VALUES (?, ?)", ("C1", "Sample"))
    connection.commit()
    connection.close()
    mapping = SourceMapping(
        type="Customer",
        kind="sqlite",
        path="data.sqlite",
        table="customer",
        id_column="id",
        columns={"name": "name"},
    )
    rows, snapshot = read_rows(mapping, tmp_path)
    assert rows == [{"id": "C1", "name": "Sample"}]
    assert len(snapshot) == 64
    mapping.path = "../outside.csv"
    with pytest.raises(ValueError, match="inside"):
        read_rows(mapping, tmp_path)


@pytest.mark.parametrize(
    "value, kind, expected",
    [
        ("3", "integer", 3),
        ("1.5", "number", 1.5),
        ("true", "boolean", True),
        ("0", "boolean", False),
        ("2026-10-01", "date", "2026-10-01"),
    ],
)
def test_source_conversion(value: str, kind: str, expected: object) -> None:
    assert convert(value, kind) == expected


@pytest.mark.parametrize(
    "value, kind",
    [("maybe", "boolean"), ("NaN", "number"), ("1.2", "integer"), ("tomorrow", "date")],
)
def test_invalid_source_values(value: str, kind: str) -> None:
    with pytest.raises(ValueError):
        convert(value, kind)


def test_proposal_workflow_never_overwrites_active_files(tmp_path: Path) -> None:
    path = propose(RETAIL / "ontology.yaml", tmp_path / "proposals")
    assert all(m.status == "draft" for m in load(path).metrics.values())
    target = tmp_path / "reviewed.yaml"
    certify(path, target, "human-reviewer")
    assert all(m.status == "certified" for m in load(target).metrics.values())
    assert target.with_suffix(".review.json").exists()
    with pytest.raises(FileExistsError):
        certify(path, target, "another-reviewer")
    with pytest.raises(ValueError, match="reviewer"):
        certify(path, tmp_path / "other.yaml", " ")


def test_csv_drafting(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    with source.open("w", newline="") as handle:
        csv.writer(handle).writerows([["id", "name"], ["1", "Example"]])
    output = tmp_path / "draft.yaml"
    draft_csv(source, "demo", "Customer", "team", output)
    ontology = load(output)
    assert ontology.types["Customer"].status == "draft"
    assert not ontology.policies
