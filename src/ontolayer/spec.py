"""Load, lint and export the public specification."""

import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import yaml
from rdflib import OWL, RDF, RDFS, XSD, Graph, Literal, Namespace, URIRef

from ontolayer.models import Ontology

SH = Namespace("http://www.w3.org/ns/shacl#")


def load(path: Path) -> Ontology:
    if path.stat().st_size > 2_000_000:
        raise ValueError("Ontology document exceeds 2 MB")
    return Ontology.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def lint(ontology: Ontology) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    for name, obj in ontology.types.items():
        if len(obj.properties) > 25:
            warnings.append({"path": name, "rule": "property-sprawl"})
        for prop, definition in obj.properties.items():
            if not definition.description:
                warnings.append({"path": f"{name}.{prop}", "rule": "missing-description"})
            if prop.startswith(("dt", "str", "tbl")) or "_" in name:
                warnings.append({"path": f"{name}.{prop}", "rule": "source-style-name"})
            if prop.endswith("_name") and prop.removesuffix("_name").title() in ontology.types:
                warnings.append({"path": f"{name}.{prop}", "rule": "embedded-entity"})
    names = list(ontology.types)
    for index, name in enumerate(names):
        for other in names[index + 1 :]:
            if SequenceMatcher(None, name.lower(), other.lower()).ratio() > 0.85:
                warnings.append({"path": f"{name}, {other}", "rule": "near-duplicate"})
    return warnings


def vocabulary(ontology: Ontology) -> Namespace:
    return Namespace(f"https://ontolayer.dev/{ontology.namespace}/")


def export_graph(ontology: Ontology) -> Graph:
    graph = Graph()
    ns = vocabulary(ontology)
    graph.bind("ol", ns)
    graph.bind("sh", SH)
    graph.bind("owl", OWL)
    graph.add((ns.ontology, RDF.type, OWL.Ontology))
    graph.add((ns.ontology, OWL.versionInfo, Literal(ontology.version)))
    datatypes = {
        "string": XSD.string,
        "integer": XSD.integer,
        "number": XSD.decimal,
        "boolean": XSD.boolean,
        "date": XSD.date,
    }
    for name, obj in ontology.types.items():
        graph.add((ns[name], RDF.type, OWL.Class))
        graph.add((ns[name], RDFS.comment, Literal(obj.description)))
        shape = ns[f"{name}Shape"]
        graph.add((shape, RDF.type, SH.NodeShape))
        graph.add((shape, SH.targetClass, ns[name]))
        for prop, definition in obj.properties.items():
            predicate = ns[f"{name}/{prop}"]
            graph.add((predicate, RDF.type, OWL.DatatypeProperty))
            graph.add((predicate, RDFS.domain, ns[name]))
            graph.add((predicate, RDFS.range, datatypes[definition.type]))
            prop_shape = ns[f"{name}Shape/{prop}"]
            graph.add((shape, SH.property, prop_shape))
            graph.add((prop_shape, SH.path, predicate))
            graph.add((prop_shape, SH.datatype, datatypes[definition.type]))
            graph.add((prop_shape, SH.maxCount, Literal(1)))
            if definition.required:
                graph.add((prop_shape, SH.minCount, Literal(1)))
    for name, link in ontology.links.items():
        graph.add((ns[name], RDF.type, OWL.ObjectProperty))
        graph.add((ns[name], RDFS.domain, ns[link.source]))
        graph.add((ns[name], RDFS.range, ns[link.target]))
        link_shape = ns[f"{name}Shape"]
        graph.add((ns[f"{link.source}Shape"], SH.property, link_shape))
        graph.add((link_shape, SH.path, ns[name]))
        graph.add((link_shape, URIRef(str(SH) + "class"), ns[link.target]))
        if link.cardinality == "one":
            graph.add((link_shape, SH.maxCount, Literal(1)))
    return graph


def write_schema(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    schema: dict[str, Any] = Ontology.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
