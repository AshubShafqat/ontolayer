"""Bounded semantic operations. Untrusted clients never receive raw backend access."""

import hashlib
import json
from collections import deque
from datetime import UTC, date, datetime
from decimal import Decimal, localcontext
from pathlib import Path
from threading import Lock
from typing import Any

from ontolayer.backend import GraphBackend, MemoryBackend
from ontolayer.models import Actor, Entity, Ontology
from ontolayer.policy import PolicyEngine
from ontolayer.requests import validate_arguments
from ontolayer.sources import ingest
from ontolayer.spec import load


class Denied(ValueError):
    """Intentionally indistinguishable missing/unauthorized resource."""


class AuditLog:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.lock = Lock()

    def record(self, actor: Actor, operation: str, outcome: str, version: str) -> None:
        event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "actor": actor.id,
            "namespace": actor.namespace,
            "operation": operation,
            "outcome": outcome,
            "ontology_version": version,
        }
        if self.path:
            with self.lock:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(event) + "\n")


class Service:
    OPERATIONS = frozenset(
        {
            "search_terms",
            "get_concept",
            "get_relationships",
            "find_path",
            "get_metric",
            "query_metric",
            "check_answerable",
            "get_lineage",
            "list_entities",
            "explain_policy_decision",
            "list_ontology_versions",
        }
    )

    def __init__(self, ontology: Ontology, backend: GraphBackend, audit: AuditLog | None = None):
        self.ontology = ontology
        self.backend = backend
        self.audit = audit or AuditLog()

    @classmethod
    def from_file(cls, path: Path, audit: AuditLog | None = None) -> "Service":
        ontology = load(path)
        backend = MemoryBackend()
        backend.apply_schema(ontology)
        ingest(ontology, path.parent, backend)
        return cls(ontology, backend, audit)

    def call(self, actor: Actor, operation: str, **arguments: Any) -> dict[str, Any]:
        try:
            if operation not in self.OPERATIONS:
                raise ValueError("Unknown operation")
            if actor.namespace != self.ontology.namespace:
                raise Denied("Not available to this caller")
            validated = validate_arguments(operation, arguments)
            result: dict[str, Any] = getattr(self, operation)(actor, **validated)
            self.audit.record(actor, operation, "allowed", self.ontology.version)
            return result
        except (ValueError, TypeError):
            self.audit.record(actor, operation, "denied_or_invalid", self.ontology.version)
            raise

    def _policy(self, actor: Actor) -> PolicyEngine:
        return PolicyEngine(self.ontology, actor)

    def _visible(self, actor: Actor) -> dict[str, Entity]:
        policy = self._policy(actor)
        return {e.id: e for e in self.backend.entities() if policy.entity_allowed(e)}

    def _page(self, items: list[Any], limit: int, offset: int) -> dict[str, Any]:
        if not 1 <= limit <= 100 or offset < 0:
            raise ValueError("limit must be 1..100 and offset must be nonnegative")
        end = offset + limit
        return {"items": items[offset:end], "next_offset": end if end < len(items) else None}

    def search_terms(
        self,
        actor: Actor,
        query: str = "",
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        policy = self._policy(actor)
        query = query.casefold()
        results = []
        for kind, definitions in (
            ("concept", self.ontology.types),
            ("metric", self.ontology.metrics),
        ):
            for name, definition in definitions.items():
                permitted = (
                    policy.type_allowed(name) if kind == "concept" else policy.metric_allowed(name)
                )
                terms = [name, definition.description, *definition.synonyms]
                if permitted and any(query in term.casefold() for term in terms):
                    results.append(
                        {
                            "id": name,
                            "kind": kind,
                            "description": definition.description,
                            "status": definition.status,
                        }
                    )
        return self._page(results, limit, offset)

    def get_concept(self, actor: Actor, concept: str) -> dict[str, Any]:
        policy = self._policy(actor)
        if not policy.type_allowed(concept):
            raise Denied("Not available to this caller")
        obj = self.ontology.types[concept]
        return {
            "id": concept,
            "description": obj.description,
            "status": obj.status,
            "synonyms": obj.synonyms,
            "owner": obj.owner,
            "properties": {
                k: v.model_dump() for k, v in obj.properties.items() if k in policy.fields(concept)
            },
        }

    def list_entities(
        self,
        actor: Actor,
        concept: str,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        policy = self._policy(actor)
        if not policy.type_allowed(concept):
            raise Denied("Not available to this caller")
        items = [policy.redact(e) for e in self._visible(actor).values() if e.type == concept]
        return self._page(sorted(items, key=lambda e: str(e["id"])), limit, offset)

    def get_relationships(
        self,
        actor: Actor,
        entity_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        visible = self._visible(actor)
        if entity_id not in visible:
            raise Denied("Not available to this caller")
        links = [
            e.model_dump()
            for e in self.backend.edges()
            if entity_id in (e.source, e.target) and e.source in visible and e.target in visible
        ]
        return self._page(links, limit, offset)

    def find_path(
        self,
        actor: Actor,
        source: str,
        target: str,
        max_depth: int = 4,
    ) -> dict[str, Any]:
        if not 1 <= max_depth <= 6:
            raise ValueError("max_depth must be 1..6")
        visible = self._visible(actor)
        if source not in visible or target not in visible:
            raise Denied("Not available to this caller")
        adjacency: dict[str, list[tuple[str, str]]] = {}
        for edge in self.backend.edges():
            if edge.source in visible and edge.target in visible:
                adjacency.setdefault(edge.source, []).append((edge.target, edge.relation))
                adjacency.setdefault(edge.target, []).append((edge.source, edge.relation))
        queue: deque[tuple[str, list[str], list[str]]] = deque([(source, [source], [])])
        visited = {source}
        while queue:
            current, path, relations = queue.popleft()
            if current == target:
                return {"nodes": path, "relations": relations, "direction": "undirected"}
            if len(relations) >= max_depth:
                continue
            for neighbor, relation in adjacency.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, [*path, neighbor], [*relations, relation]))
        return {"nodes": [], "relations": [], "direction": "undirected"}

    def get_metric(self, actor: Actor, metric_id: str) -> dict[str, Any]:
        policy = self._policy(actor)
        if not policy.metric_allowed(metric_id):
            raise Denied("Not available to this caller")
        metric = self.ontology.metrics[metric_id]
        fields = set(metric.fields + metric.dimensions + list(metric.filters))
        if metric.date_field:
            fields.add(metric.date_field)
        if not fields <= policy.fields(metric.type):
            raise Denied("Not available to this caller")
        return {"id": metric_id, **metric.model_dump(), "ontology_version": self.ontology.version}

    def query_metric(
        self,
        actor: Actor,
        metric_id: str,
        filters: dict[str, Any] | None = None,
        group_by: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        self.get_metric(actor, metric_id)
        metric = self.ontology.metrics[metric_id]
        if metric.status != "certified":
            raise ValueError("Metric is a draft; a human must certify it before execution")
        filters = filters or {}
        if not set(filters) <= set(metric.dimensions):
            raise ValueError("Filter must be a declared metric dimension")
        if group_by is not None and group_by not in metric.dimensions:
            raise ValueError("Grouping must be a declared metric dimension")
        if any(not isinstance(v, (str, int, float, bool)) for v in filters.values()):
            raise ValueError("Filter values must be scalar")
        if (start_date or end_date) and not metric.date_field:
            raise ValueError("Metric does not support date filtering")
        if start_date:
            start_date = date.fromisoformat(start_date).isoformat()
        if end_date:
            end_date = date.fromisoformat(end_date).isoformat()
        if start_date and end_date and start_date >= end_date:
            raise ValueError("Date interval must have start < exclusive end")
        policy = self._policy(actor)
        rows = []
        required = set(metric.fields + list(metric.filters) + list(filters))
        if group_by:
            required.add(group_by)
        if metric.date_field:
            required.add(metric.date_field)
        for entity in self._visible(actor).values():
            if entity.type != metric.type:
                continue
            if not required <= policy.fields(entity.type, entity):
                raise Denied("Not available to this caller")
            props = entity.properties
            if not all(props.get(k) == v for k, v in metric.filters.items()):
                continue
            if not all(props.get(k) == v for k, v in filters.items()):
                continue
            if not required <= props.keys():
                raise ValueError("Source is missing a required metric value")
            when = str(props.get(metric.date_field or "", ""))
            if (start_date and when < start_date) or (end_date and when >= end_date):
                continue
            rows.append(entity)
        groups: dict[str, Decimal] = {} if group_by else {"total": Decimal(0)}
        with localcontext() as context:
            context.prec = 80
            for entity in rows:
                key = str(entity.properties[group_by]) if group_by else "total"
                amount = Decimal(1)
                for field in metric.fields:
                    amount *= Decimal(str(entity.properties[field]))
                groups[key] = groups.get(key, Decimal(0)) + amount
        if len(groups) > 100:
            raise ValueError("More than 100 groups; narrow the filters")
        lineage = sorted({(e.source, e.mapping, e.snapshot) for e in rows})
        return {
            "metric": metric_id,
            "values": {k: str(v) for k, v in sorted(groups.items())},
            "unit": metric.unit,
            "status": metric.status,
            "grain": metric.grain,
            "scope": "authorized records only",
            "filters": filters,
            "group_by": group_by,
            "start_date": start_date,
            "end_date_exclusive": end_date,
            "ontology_version": self.ontology.version,
            "namespace": self.ontology.namespace,
            "lineage": [{"source": s, "mapping": m, "snapshot_sha256": h} for s, m, h in lineage],
            "definition_sha256": hashlib.sha256(metric.model_dump_json().encode()).hexdigest(),
        }

    def check_answerable(self, actor: Actor, metric_id: str) -> dict[str, Any]:
        try:
            metric = self.get_metric(actor, metric_id)
        except Denied:
            return {"answerable": False, "reason": "No available certified metric for this request"}
        certified = metric["status"] == "certified"
        return {"answerable": certified, "reason": "ready" if certified else "Metric is a draft"}

    def get_lineage(self, actor: Actor, entity_id: str) -> dict[str, Any]:
        entity = self._visible(actor).get(entity_id)
        if entity is None:
            raise Denied("Not available to this caller")
        return {
            "entity": entity.id,
            "source": entity.source,
            "mapping": entity.mapping,
            "snapshot_sha256": entity.snapshot,
            "ontology_version": self.ontology.version,
            "status": self.ontology.types[entity.type].status,
        }

    def explain_policy_decision(
        self,
        actor: Actor,
        entity_id: str,
    ) -> dict[str, Any]:
        allowed = entity_id in self._visible(actor)
        return {
            "allowed": allowed,
            "reason": "Visible under caller policy" if allowed else "Not available to this caller",
        }

    def list_ontology_versions(self, actor: Actor) -> dict[str, Any]:
        if not self._policy(actor).rules:
            raise Denied("Not available to this caller")
        return {
            "namespace": self.ontology.namespace,
            "active_version": self.ontology.version,
            "versions": [self.ontology.version],
        }
