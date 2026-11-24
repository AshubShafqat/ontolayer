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
        """Search permitted business concepts and metrics, including synonyms."""
        return service.call(actor, "search_terms", query=query, limit=limit, offset=offset)

    @server.tool()
    def get_concept(concept: str) -> dict[str, Any]:
        """Get a concept's definition and permitted properties."""
        return service.call(actor, "get_concept", concept=concept)

    @server.tool()
    def list_entities(concept: str, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        """List authorized entity records; pagination never counts hidden records."""
        return service.call(actor, "list_entities", concept=concept, limit=limit, offset=offset)

    @server.tool()
    def get_relationships(entity_id: str, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        """Find links whose endpoints are both visible to the caller."""
        return service.call(
            actor, "get_relationships", entity_id=entity_id, limit=limit, offset=offset
        )

    @server.tool()
    def find_path(source: str, target: str, max_depth: int = 4) -> dict[str, Any]:
        """Find an undirected path inside the authorized subgraph (at most six hops)."""
        return service.call(actor, "find_path", source=source, target=target, max_depth=max_depth)

    @server.tool()
    def get_metric(metric_id: str) -> dict[str, Any]:
        """Read a governed metric definition; this does not execute it."""
        return service.call(actor, "get_metric", metric_id=metric_id)

    @server.tool()
    def query_metric(
        metric_id: str,
        filters: dict[str, Any] | None = None,
        group_by: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Execute a certified metric over authorized records, returning values and lineage."""
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
        """Check whether the caller can use this certified metric."""
        return service.call(actor, "check_answerable", metric_id=metric_id)

    @server.tool()
    def get_lineage(entity_id: str) -> dict[str, Any]:
        """Read provenance only for a visible entity."""
        return service.call(actor, "get_lineage", entity_id=entity_id)

    @server.tool()
    def explain_policy_decision(entity_id: str) -> dict[str, Any]:
        """Explain visibility without revealing whether a hidden entity exists."""
        return service.call(actor, "explain_policy_decision", entity_id=entity_id)

    @server.tool()
    def list_ontology_versions() -> dict[str, Any]:
        """Get the ontology version loaded by this immutable server instance."""
        return service.call(actor, "list_ontology_versions")

    return server
