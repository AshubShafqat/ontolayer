# Security policy

Report vulnerabilities privately through this repository's GitHub Security Advisories when enabled,
or contact the repository owner privately. Do not include sensitive data in public issues.

This is a working reference implementation, not a certified enterprise security product.
The deployment owner controls ontology documents, mapping paths, actor files, credentials,
the source directory, and the local process account. These are trusted configuration.
Untrusted users receive semantic tools, not filesystem access or the maintainer CLI.

- MCP uses local stdio. The trusted launcher chooses a fixed actor; tools cannot change identity.
- REST uses opaque bearer tokens checked against SHA-256 digests in a server-owned credential file.
- Public demo tokens are deliberately documented and only suitable for synthetic examples.
- Default-deny grants restrict type access, properties, metrics, and row attributes.
- Row filtering occurs before traversal and aggregation; PII is omitted without explicit permission.
- All source paths must stay below the ontology directory. Only read-only SQLite SELECT is used.
- Metric expressions are bounded operations, not arbitrary SQL/SPARQL/Python evaluation.
- Audit records contain actor, namespace, operation, outcome, and version, not query values.

For deployment, use TLS at a reverse proxy, private source storage, random tokens, OS access control,
rate/request-size limits, and audit-log retention/access controls. One immutable service instance
serves one namespace. Tenant isolation is not a substitute for separately isolating data stores.
Token rotation means replacing/removing the digest entry; authentication reloads the file per request.
There is no OIDC/JWT federation, distributed rate limiting, or external security audit in v0.1.
Source-file hashes are provenance, not access-controlled exports of source contents.
Do not host this demo with public credentials or expose a maintainer actor to an untrusted agent.
