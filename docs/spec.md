# Ontology specification

The normative machine-readable structure is [`spec/ontology.schema.json`](../spec/ontology.schema.json).
Unknown keys are rejected. The loader also checks cross-references and numeric metric operands.
See the complete [retail example](../examples/retail/ontology.yaml).

| Element | Meaning |
| --- | --- |
| namespace, version | Tenant/domain identifier and semantic version |
| types | Business object definitions, owners, descriptions, status and properties |
| properties | string, integer, number, boolean or date; required flag, description, PII and unit |
| interfaces | Named property contracts; implementing types must supply compatible fields |
| links | Directed typed relationships; `one` constrains maximum outgoing targets to one |
| mappings | Source file/table, identity column, property-to-column mapping and foreign-key links |
| metrics | Reviewed type/grain, aggregation, fields, immutable base filters, dimensions and dates |
| policies | Explicit role grants, property grants, metric grants, and row-attribute comparisons |

Metric date intervals use inclusive start and exclusive end. `2026-10-01` to `2026-11-01`
means October. Request filters may only use declared dimensions and cannot replace the metric's
base filters. `group_by` supports one declared dimension and at most 100 groups. Uncertified
metrics are discoverable as drafts when permitted, but cannot execute.

Validation checks structure and references. SHACL checks loaded data, required properties,
datatypes, relationship target types, and single-valued links. Lint findings are advisory:
missing descriptions, source-like names, embedded entities, excessive properties and near-duplicate
type names. It does not claim to infer business correctness or detect every table mirror.

Source paths are relative to the ontology file and cannot escape its directory. SQLite mappings
set `kind: sqlite`, `path: demo.sqlite`, and `table: orders`. The adapter uses a quoted table name,
a read-only connection, and explicit source-to-property mapping. CSV uses UTF-8 with optional BOM.

Business IDs must be unique per type; duplicate source rows and dangling references fail the build.
Missing optional fields are omitted. Empty required fields fail graph validation.
