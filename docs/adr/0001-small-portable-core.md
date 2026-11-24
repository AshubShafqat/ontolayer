# ADR 0001: a small deterministic core with MCP at the boundary

Status: accepted for v0.1.

The project needs to demonstrate ontology-as-code, source mapping, graph traversal, governed
metrics and agent interoperability without an infrastructure prerequisite. Use Python, Pydantic,
YAML/JSON Schema, RDFLib/SHACL and a shared semantic service. Begin with CSV and read-only SQLite.
Expose bounded tools over official MCP stdio and authenticated FastAPI. Use LangGraph to compose
the reference agent, with a deterministic demo planner and optional model planning.

Consequences: contributors can run a complete example locally, and policy tests have predictable
fixtures. The backend is not durable or warehouse-scale. RDF export covers schema structure but
does not encode every runtime policy. New backends must satisfy a tested operation contract.

Do not add mandatory Docker, a proprietary model API, or agent-generated SQL to the core path.
Adopt remote storage, federated identity and horizontal deployment only with conformance and
security tests that demonstrate the needed guarantees.
