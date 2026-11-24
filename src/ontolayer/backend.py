"""Backend contract and a validated in-process RDF implementation."""

from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from typing import Protocol
from urllib.parse import quote

from pyshacl import validate
from rdflib import RDF, XSD, Graph, Literal, URIRef

from ontolayer.models import Edge, Entity, Ontology
from ontolayer.spec import export_graph, vocabulary


class GraphBackend(Protocol):
    def apply_schema(self, ontology: Ontology) -> None: ...
    def upsert(self, entities: Iterable[Entity], edges: Iterable[Edge]) -> None: ...
    def entities(self) -> list[Entity]: ...
    def edges(self) -> list[Edge]: ...
    def export(self) -> str: ...


class MemoryBackend:
    """Atomic batch replacement/upsert with SHACL validation before publication."""

    def __init__(self) -> None:
        self.ontology: Ontology | None = None
        self._entities: dict[str, Entity] = {}
        self._edges: dict[tuple[str, str, str], Edge] = {}
        self.graph = Graph()

    def apply_schema(self, ontology: Ontology) -> None:
        if self._entities:
            raise ValueError("Create a new backend to migrate a populated schema")
        self.ontology = ontology

    def upsert(self, entities: Iterable[Entity], edges: Iterable[Edge]) -> None:
        if self.ontology is None:
            raise ValueError("Apply schema before writing")
        candidates = {**self._entities, **{e.id: e for e in entities}}
        links = dict(self._edges)
        for edge in edges:
            links[(edge.source, edge.relation, edge.target)] = edge
        graph = Graph()
        ns = vocabulary(self.ontology)

        def node(entity_id: str) -> URIRef:
            return ns[f"entity/{quote(entity_id, safe='')}"]

        for entity in candidates.values():
            if entity.type not in self.ontology.types:
                raise ValueError("Unknown entity type")
            graph.add((node(entity.id), RDF.type, ns[entity.type]))
            props = self.ontology.types[entity.type].properties
            for key, value in entity.properties.items():
                if key not in props:
                    raise ValueError("Unknown entity property")
                datatype = props[key].type
                literal = Literal(value)
                if datatype == "number":
                    number = Decimal(str(value))
                    if not number.is_finite():
                        raise ValueError("Non-finite numbers are not supported")
                    literal = Literal(number, datatype=XSD.decimal)
                elif datatype == "date":
                    literal = Literal(date.fromisoformat(str(value)), datatype=XSD.date)
                graph.add((node(entity.id), ns[f"{entity.type}/{key}"], literal))
        for edge in links.values():
            if edge.source not in candidates or edge.target not in candidates:
                raise ValueError("Dangling relationship")
            definition = self.ontology.links.get(edge.relation)
            if definition is None:
                raise ValueError("Unknown relationship")
            if (candidates[edge.source].type, candidates[edge.target].type) != (
                definition.source,
                definition.target,
            ):
                raise ValueError("Relationship endpoint type mismatch")
            graph.add((node(edge.source), ns[edge.relation], node(edge.target)))
        conforms, _, _ = validate(graph, shacl_graph=export_graph(self.ontology))
        if not conforms:
            raise ValueError("Data failed SHACL validation; check required fields and value types")
        self._entities, self._edges, self.graph = candidates, links, graph

    def entities(self) -> list[Entity]:
        return [e.model_copy(deep=True) for e in self._entities.values()]

    def edges(self) -> list[Edge]:
        return [e.model_copy() for e in self._edges.values()]

    def export(self) -> str:
        return self.graph.serialize(format="turtle")
