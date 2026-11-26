# Deploying an operated OntoLayer workspace

Version 0.3 includes a web application and an administrator draft/publication workbench for
a small workspace with one application writer. Production readiness depends on your identity system,
data quality, traffic, infrastructure, recovery procedure and security review; running demo data
on localhost does not establish those properties.

## Application and authentication

The product is at `/`. `/docs` is a developer interface, disabled with `--production`.
Without `--demo`, the web UI asks for a token. Credentials stay in page memory and are cleared
on sign-out or reload; they are never written to local/session storage or URLs. The server resolves
the actor from a server-owned digest file on each request, allowing immediate revocation.

Create a private actor file based on the required policies. Issue a random token:

```sh
uv run ontolayer issue-token --actor /private/actor.yaml --output /private/credentials.yaml
```

Distribute the printed token using an approved secret-sharing channel. Do not put the actor or
credential file in Git. Grant the process account read-only access. Grant write access only to
its audit and workspace directories. The production profile refuses known demo tokens, an absent audit log,
wildcard hosts and the demo identity switcher.

```sh
uv run ontolayer serve --ontology /data/ontology.yaml --credentials /private/credentials.yaml --production --allowed-host ontology.example.com --audit /state/audit.jsonl --workspace-directory /state/workspace
```

The process serves one namespace and validated snapshot. Administrators can preview JSON/YAML
definitions and bounded CSV uploads, then explicitly certify to activate a durable release. Preview
cannot publish, stale revisions are rejected, and arbitrary browser-selected paths cannot be read.
Only trusted administrators should receive the admin role: raw definitions, source uploads and
policy edits are powerful capabilities. Use one worker and one writer per workspace directory.
Back up the entire workspace tree, initial ontology/source directory, audit and credential stores.
Keep prior release directories for rollback. To roll back, stop the server and restore a backed-up
active pointer and its complete release directory, then restart and verify version and query results.

## Container deployment

The Docker build uses the committed Python lockfile, a non-root runtime user and a healthcheck.
The sample production Compose profile adds a read-only root filesystem, dropped capabilities,
private source/credential mounts, persistent audit storage and Caddy for HTTPS.

Set `APP_HOST` to a real domain pointing to the server, `ONTOLOGY_DATA_DIR` to the reviewed data
directory, and `ONTOLOGY_CREDENTIALS` to your private credential file. Paths must be absolute.
Ensure the runtime user (UID 1000) can read the two mounts. Then run:

```sh
docker compose -f deploy/compose.production.yaml up --build -d
```

This configuration is supplied for operator review; the current development environment has not
provisioned a public domain, certificates or a production host. Pin the reviewed base/proxy images
by digest for your release process and scan the built image in your infrastructure.

## Boundaries and operational requirements

- Security headers restrict product scripts, styles and connections to the same origin. HTML
  cannot frame the application, and authenticated responses use `Cache-Control: no-store`.
- Semantic inputs have strict types, length/page/hop bounds and no additional fields. Request
  bodies are capped at 64 KiB, including chunked requests. The API admits at most 240 requests
  per client IP per minute per process, and Uvicorn limits concurrency to 100.
- Put stronger rate limits at your ingress for a public service. The in-process limiter is not
  distributed; behind a proxy, it may see the proxy IP, sharing a quota across callers. Do not
  trust forwarded IP headers from untrusted peers. Configure your ingress before increasing load.
- `/health` means the validated snapshot has loaded. Monitor it, process restarts, request latency,
  memory, disk space and error rates. Authenticated operators can read Prometheus `/metrics`.
- Audit logs persist semantic request metadata, not sensitive result bodies. Protect, rotate,
  ship and retain them under your own policy. They are not tamper-evident. Use one worker per
  audit file, or replace this sink with a coordinated logging service before scaling workers.
- The RDF graph is held in memory and rebuilt from durable source snapshots. Certified releases
  persist; the current-process audit ring does not. There is no clustered graph database.
  Draft/release disk retention and quotas are operator responsibilities. Benchmark real data before
  setting latency or availability targets. Paginated responses do not make ingestion streaming.
- CSV numeric inputs use Decimal rather than binary float conversion. SQLite REAL values have
  already passed through binary floating point; store precise financial source values as TEXT.
- Token authentication is supported; enterprise SSO/OIDC, multi-factor policies, and a user
  provisioning service are not included. Add these at the trusted identity boundary if required.

## Validation before rollout

CI runs semantic/security tests, strict typing, linting, real MCP questions, browser journeys,
automated WCAG AA checks, dependency audit/SBOM and package builds. Browser tests cover role
switching, restricted records/PII, lineage, queries, downloads, sign-in/out and mobile overflow.
Automated accessibility checks do not replace keyboard and assistive-technology review.

For your deployment, additionally verify TLS, token revocation, private-data access rules, backup
restoration, snapshot rollback, ingress limits, load behavior and audit retention. Live model
providers remain optional and require their own reliability/privacy evaluation. No independent
penetration test or production SLO is claimed by this release.
