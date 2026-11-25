"""Strict, bounded input contracts shared by REST, MCP and local callers."""

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

Name = Annotated[str, Field(min_length=1, max_length=200)]


class Arguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class PageArguments(Arguments):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=1_000_000)


class SearchArguments(PageArguments):
    query: str = Field(default="", max_length=500)


class ConceptArguments(Arguments):
    concept: Name


class EntityListArguments(PageArguments):
    concept: Name


class EntityArguments(Arguments):
    entity_id: Name


class RelationshipArguments(PageArguments):
    entity_id: Name


class PathArguments(Arguments):
    source: Name
    target: Name
    max_depth: int = Field(default=4, ge=1, le=6)


class MetricArguments(Arguments):
    metric_id: Name


class QueryArguments(MetricArguments):
    filters: dict[Name, str | int | float | bool] | None = Field(default=None, max_length=20)
    group_by: Name | None = None
    start_date: Annotated[str, Field(max_length=10)] | None = None
    end_date: Annotated[str, Field(max_length=10)] | None = None


CONTRACTS: dict[str, type[Arguments]] = {
    "search_terms": SearchArguments,
    "get_concept": ConceptArguments,
    "list_entities": EntityListArguments,
    "get_relationships": RelationshipArguments,
    "find_path": PathArguments,
    "get_metric": MetricArguments,
    "query_metric": QueryArguments,
    "check_answerable": MetricArguments,
    "get_lineage": EntityArguments,
    "explain_policy_decision": EntityArguments,
    "list_ontology_versions": Arguments,
}


def validate_arguments(operation: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return CONTRACTS[operation].model_validate(arguments).model_dump()
