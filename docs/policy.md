# Policies and identities

## Administrator publication in v0.3

The trusted credential role `admin` additionally enables raw definition export, draft validation,
CSV upload previews and explicit certification. This is a management capability, not a semantic
tool argument. Treat administrators as trusted ontology/policy owners. All candidate definitions
remain drafts until certification; stale revisions and invalid graphs cannot replace active state.
The operator role permits namespace-wide audit metadata; ordinary callers see their own events.
The browser comparison uses separate public synthetic credentials and is unavailable outside demo mode.

## Semantic grants

Each policy explicitly grants a role access to types, properties and metric IDs. An absent grant
denies access. Row constraints bind business properties to trusted actor attributes.

```yaml
role: regional
types: [OrderLine]
metrics: [revenue]
properties:
  OrderLine: [quantity, unit_price, status, date, region]
row_attributes:
  region: region
allow_pii: false
```

The example permits a regional actor with `attributes: {region: north}` to read and aggregate only
north records. The server, not an MCP argument, supplies those attributes. Multiple rules are
additive, so assigning a global admin role intentionally grants global access.

The service validates metric input fields against field permissions and filters rows before
computing results. Relationships require both endpoints to be visible. Missing and forbidden
entity identifiers have the same public error. Metadata/property discovery and lineage are
filtered too. Do not expose confidential details in shared concept descriptions or metric names.

For REST, create a server-owned credential file with `ontolayer issue-token --actor ACTOR.yaml
--output CREDENTIALS.yaml`. Store the printed random token securely. The file stores only its digest.
Merge credential entries administratively when multiple callers are needed. Demo fixtures use
known tokens (`demo-admin-token`, `demo-north-token`, etc.) solely for reproducibility.

MCP stdio trusts the launcher's actor file and process boundary. A user with local filesystem
access to edit that file already controls the service, so do not treat it as authentication for
hostile local users. For multiple remote users, use the authenticated REST surface behind TLS.

The audit JSONL logs operation, caller, namespace, outcome and version. Protect it with OS
permissions and retention rules. It intentionally excludes request/result payloads. It is not
tamper-evident. See [SECURITY.md](../SECURITY.md) for deployment limits.
