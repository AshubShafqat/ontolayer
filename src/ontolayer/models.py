"""The ontology document is the public, versioned contract."""

import re
from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Scalar = str | int | float | bool | Decimal
Status = Literal["draft", "certified"]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Property(Model):
    type: Literal["string", "integer", "number", "boolean", "date"] = "string"
    description: str = ""
    required: bool = False
    pii: bool = False
    unit: str | None = None


class ObjectType(Model):
    description: str
    owner: str
    properties: dict[str, Property]
    synonyms: list[str] = Field(default_factory=list)
    interfaces: list[str] = Field(default_factory=list)
    status: Status = "draft"


class Interface(Model):
    description: str
    properties: dict[str, Property]


class LinkType(Model):
    source: str
    target: str
    description: str
    cardinality: Literal["many", "one"] = "many"


class SourceMapping(Model):
    type: str
    kind: Literal["csv", "sqlite"] = "csv"
    path: str
    table: str | None = None
    id_column: str
    columns: dict[str, str]
    links: dict[str, str] = Field(default_factory=dict)


class Metric(Model):
    description: str
    owner: str
    type: str
    aggregation: Literal["count", "sum", "sum_product"]
    fields: list[str] = Field(default_factory=list)
    filters: dict[str, Scalar] = Field(default_factory=dict)
    dimensions: list[str] = Field(default_factory=list)
    date_field: str | None = None
    unit: str
    grain: str
    synonyms: list[str] = Field(default_factory=list)
    status: Status = "draft"


class Policy(Model):
    role: str
    types: list[str]
    metrics: list[str] = Field(default_factory=list)
    properties: dict[str, list[str]] = Field(default_factory=dict)
    row_attributes: dict[str, str] = Field(default_factory=dict)
    allow_pii: bool = False


class Ontology(Model):
    namespace: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    description: str
    types: dict[str, ObjectType]
    links: dict[str, LinkType] = Field(default_factory=dict)
    interfaces: dict[str, Interface] = Field(default_factory=dict)
    mappings: dict[str, SourceMapping] = Field(default_factory=dict)
    metrics: dict[str, Metric] = Field(default_factory=dict)
    policies: list[Policy] = Field(default_factory=list)

    @model_validator(mode="after")
    def references(self) -> Self:
        for names in (self.types, self.links, self.interfaces, self.mappings, self.metrics):
            if any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", n) for n in names):
                raise ValueError("Names must be identifiers beginning with a letter")
        for name, obj in self.types.items():
            if not obj.owner.strip() or not obj.description.strip():
                raise ValueError(f"{name} requires owner and description")
            for interface in obj.interfaces:
                if interface not in self.interfaces:
                    raise ValueError(f"Unknown interface: {interface}")
                for prop, expected in self.interfaces[interface].properties.items():
                    actual = obj.properties.get(prop)
                    if actual is None or actual.type != expected.type:
                        raise ValueError(f"{name} does not implement {interface}.{prop}")
        for link in self.links.values():
            if link.source not in self.types or link.target not in self.types:
                raise ValueError("Link endpoint type does not exist")
        for mapping in self.mappings.values():
            if mapping.type not in self.types:
                raise ValueError("Mapping type does not exist")
            if not set(mapping.columns) <= self.types[mapping.type].properties.keys():
                raise ValueError("Mapping references unknown property")
            for link_name in mapping.links:
                if link_name not in self.links or self.links[link_name].source != mapping.type:
                    raise ValueError("Mapping link has wrong source type")
            if mapping.kind == "sqlite" and not mapping.table:
                raise ValueError("SQLite mapping requires a table")
        for metric in self.metrics.values():
            if metric.type not in self.types:
                raise ValueError("Metric type does not exist")
            properties = self.types[metric.type].properties
            refs = metric.fields + metric.dimensions + list(metric.filters)
            if metric.date_field:
                refs.append(metric.date_field)
                if properties.get(metric.date_field, Property()).type != "date":
                    raise ValueError("Metric date_field must have date type")
            if not set(refs) <= properties.keys():
                raise ValueError("Metric references unknown property")
            expected_count = {"count": 0, "sum": 1, "sum_product": 2}[metric.aggregation]
            if len(metric.fields) != expected_count:
                raise ValueError("Metric aggregation has incorrect field count")
            if any(properties[f].type not in {"integer", "number"} for f in metric.fields):
                raise ValueError("Metric operands must be numeric")
        for policy in self.policies:
            if not set(policy.types) <= self.types.keys():
                raise ValueError("Policy references unknown type")
            if not set(policy.metrics) <= self.metrics.keys():
                raise ValueError("Policy references unknown metric")
            for type_name, fields in policy.properties.items():
                if type_name not in policy.types:
                    raise ValueError("Policy property type is not granted")
                if not set(fields) <= self.types[type_name].properties.keys():
                    raise ValueError("Policy references unknown property")
            for type_name in policy.types:
                if not set(policy.row_attributes) <= self.types[type_name].properties.keys():
                    raise ValueError("Row policy property must exist on every granted type")
        return self


class Actor(Model):
    id: str
    namespace: str
    roles: list[str] = Field(default_factory=list)
    attributes: dict[str, Scalar] = Field(default_factory=dict)


class Entity(Model):
    id: str
    type: str
    properties: dict[str, Scalar]
    source: str
    mapping: str
    snapshot: str


class Edge(Model):
    source: str
    relation: str
    target: str
