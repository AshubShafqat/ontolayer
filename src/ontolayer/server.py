"""MCP stdio transport: actor configuration belongs to the trusted launcher."""

from typing import Any

from mcp.server.fastmcp import FastMCP

from ontolayer.models import Actor
from ontolayer.service import Service


def create_mcp(service: Service, actor: Actor) -> FastMCP:
    server = FastMCP(
        "OntoLayer",
        log_level="WARNING",
        instructions=(
            "Use search_terms to resolve business vocabulary. "
            "Use check_answerable before query_metric, "
            "and preserve lineage, scope, units and certification in answers. "
            "Dates are ISO dates with an exclusive end. Never infer inaccessible data."
        ),
    )

    @server.tool()
    def search_terms(query: str = "", limit: int = 20, offset: int = 0) -> dict[str, Any]:
        """Search permitted concepts and metrics by names, descriptions or synonyms.
        Arguments: query: str (default "", max 500 characters); limit: int (1..100,
        default 20); offset: int (0..1000000, default 0). Hidden definitions and
        counts are excluded. Example: search_terms(query="sales", limit=10).
        Returns: {items: [{id, kind, description, status}], next_offset: int|null}."""
        return service.call(actor, "search_terms", query=query, limit=limit, offset=offset)

    @server.tool()
    def get_concept(concept: str) -> dict[str, Any]:
        """Read a permitted business definition without retrieving entity records.
        Arguments: concept: str (1..200 characters). Example: get_concept(concept="Customer").
        Hidden fields are omitted; missing and forbidden concepts produce the same denial.
        Returns: {id, description, status, synonyms, owner, properties: object}."""
        return service.call(actor, "get_concept", concept=concept)

    @server.tool()
    def list_entities(concept: str, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        """List authorized records of one concept, with permitted properties only.
        Arguments: concept: str (1..200 characters, not concept_id); limit: int
        (1..100, default 20); offset: int (0..1000000, default 0).
        Hidden records never contribute to pagination or counts; unavailable types are denied.
        Example: list_entities(concept="Customer", limit=20, offset=0).
        Returns: {items: [{id, type, properties}], next_offset: int|null}."""
        return service.call(actor, "list_entities", concept=concept, limit=limit, offset=offset)

    @server.tool()
    def get_relationships(entity_id: str, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        """List links incident to an authorized entity; both endpoints must be visible.
        Arguments: entity_id: str (1..200 characters); limit: int (1..100, default 20);
        offset: int (0..1000000, default 0). Missing and hidden entities are indistinguishable.
        Example: get_relationships(entity_id="Customer:C1", limit=10).
        Returns: {items: [{source, target, relation}], next_offset: int|null}; no hidden counts."""
        return service.call(
            actor, "get_relationships", entity_id=entity_id, limit=limit, offset=offset
        )

    @server.tool()
    def find_path(source: str, target: str, max_depth: int = 4) -> dict[str, Any]:
        """Find an undirected path inside the caller's authorized subgraph.
        Arguments: source: str and target: str (each 1..200 characters);
        max_depth: int (1..6 hops, default 4). Hidden and missing endpoints are denied alike.
        Example: find_path(source="Customer:C1", target="Order:O1", max_depth=4).
        Returns: {nodes: [str], relations: [str], direction: "undirected"};
        empty arrays mean no visible path within the bound, never a hidden path count."""
        return service.call(actor, "find_path", source=source, target=target, max_depth=max_depth)

    @server.tool()
    def get_metric(metric_id: str) -> dict[str, Any]:
        """Read a permitted metric definition without executing it.
        Arguments: metric_id: str (1..200 characters). Example: get_metric(metric_id="revenue").
        Missing metrics, denied metrics and inaccessible calculation fields are denied alike.
        Returns: {id, ontology_version, description, type, aggregation, fields, dimensions,
        filters, date_field, unit, grain, status, owner, synonyms} (definition fields)."""
        return service.call(actor, "get_metric", metric_id=metric_id)

    @server.tool()
    def query_metric(
        metric_id: str,
        filters: dict[str, Any] | None = None,
        group_by: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Calculate a certified metric on authorized records, with source evidence.
        Arguments: metric_id: str (1..200 chars); filters: object|null (default null,
        at most 20 declared dimension keys, each 1..200 chars, scalar str/int/float/bool
        values); group_by: str|null (declared dimension, 1..200 chars, default null);
        start_date: str|null and end_date: str|null (ISO YYYY-MM-DD, default null).
        Start is inclusive; end exclusive; absent dates mean all dates. At most 100 groups.
        Draft metrics cannot execute. Hidden rows, fields and lineage never contribute.
        Example: query_metric(metric_id="revenue", start_date="2026-10-01",
        end_date="2026-11-01"). Returns: {metric, values: {group: decimal_string}, unit,
        status, grain, scope, filters, group_by, start_date, end_date_exclusive,
        ontology_version, namespace, lineage: [{source, mapping, snapshot_sha256}],
        definition_sha256}."""
        return service.call(
            actor,
            "query_metric",
            metric_id=metric_id,
            filters=filters,
            group_by=group_by,
            start_date=start_date,
            end_date=end_date,
        )

    @server.tool()
    def check_answerable(metric_id: str) -> dict[str, Any]:
        """Check whether a certified metric is available before attempting calculation.
        Arguments: metric_id: str (1..200 characters).
        Example: check_answerable(metric_id="revenue"). Returns: {answerable: bool, reason: str}.
        Missing and unauthorized definitions return the same negative response;
        no metric definition or record count is disclosed. Draft metrics are not answerable."""
        return service.call(actor, "check_answerable", metric_id=metric_id)

    @server.tool()
    def get_lineage(entity_id: str) -> dict[str, Any]:
        """Return provenance for one visible entity, without private source contents.
        Arguments: entity_id: str (1..200 characters).
        Example: get_lineage(entity_id="Customer:C1"). Missing and hidden entities are denied alike.
        Returns: {entity, source, mapping, snapshot_sha256, ontology_version, status}."""
        return service.call(actor, "get_lineage", entity_id=entity_id)

    @server.tool()
    def explain_policy_decision(entity_id: str) -> dict[str, Any]:
        """Explain visibility without disclosing whether an inaccessible record exists.
        Arguments: entity_id: str (1..200 characters).
        Example: explain_policy_decision(entity_id="Customer:C1").
        Returns: {allowed: bool, reason: str}; missing and hidden records share the exact
        negative response with no record properties, policy details or counts."""
        return service.call(actor, "explain_policy_decision", entity_id=entity_id)

    @server.tool()
    def list_ontology_versions() -> dict[str, Any]:
        """Describe the single ontology snapshot loaded by this MCP process.
        Arguments: none. Example: list_ontology_versions().
        Returns: {namespace: str, active_version: str, versions: [str]} (one version).
        Callers without namespace policy grants are denied. This is not release history;
        restart the MCP process to load a newly certified snapshot."""
        return service.call(actor, "list_ontology_versions")

    return server
